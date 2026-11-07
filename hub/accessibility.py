"""Background UI Automation: Invoke/Value patterns, never mouse/keyboard injection."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time,uuid
from .errors import ObservationError

class Accessibility:
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='uia-owner')
        self.initialized=False;self.snapshot=None
    def initialize(self):
        if not self.initialized:
            import pythoncom
            pythoncom.CoInitialize()
            from pywinauto import Desktop
            self.desktop=Desktop(backend='uia');self.initialized=True
    async def inspect(self,hwnd):
        for attempt in range(3):
            try:return await asyncio.get_running_loop().run_in_executor(self.executor,self._inspect,hwnd)
            except Exception as exc:
                if attempt==2:raise ObservationError('Window controls changed while reading. Inspect the same window again. '+str(exc)) from exc
                await asyncio.sleep(.3)
    def _inspect(self,hwnd):
        self.initialize()
        window=self.desktop.window(handle=hwnd).wrapper_object()
        elements=[];refs={}
        all_controls=window.descendants()
        tabs=[]
        for control in all_controls:
            if control.element_info.control_type=='TabItem':
                try:selected=bool(control.iface_selection_item.CurrentIsSelected)
                except Exception:selected=None
                tabs.append({'title':control.window_text(),'selected':selected,'source':'Windows UI Automation'})
        # Prioritize tab controls so large documents cannot hide other tabs from the agent.
        all_controls.sort(key=lambda c:0 if c.element_info.control_type=='Window' else (1 if c.element_info.control_type=='TabItem' else 2))
        for control in all_controls:
            if len(elements)>=300:break
            try:
                info=control.element_info
                rectangle=control.rectangle()
                if info.control_type!='TabItem' and (info.element.CurrentIsOffscreen or rectangle.width()<=0 or rectangle.height()<=0):continue
                ref='u'+str(len(elements)+1)
                password=bool(info.element.CurrentIsPassword)
                item={'ref':ref,'type':info.control_type,'name':info.name[:200],'enabled':control.is_enabled(),'password':password,'bounds':{'left':rectangle.left,'top':rectangle.top,'width':rectangle.width(),'height':rectangle.height()}}
            except Exception:continue
            if info.control_type=='Edit' and not password:
                try:item['value']=control.iface_value.CurrentValue[:1000]
                except Exception:pass
            if info.control_type=='TabItem':
                try:item['selected']=bool(control.iface_selection_item.CurrentIsSelected)
                except Exception:item['selected']=None
            if info.control_type=='Document' and not password:
                try:item['value']=control.iface_text.DocumentRange.GetText(4000)
                except Exception:pass
            if info.control_type=='Window':
                try:item['modal']=bool(control.iface_window.CurrentIsModal)
                except Exception:item['modal']=None
            if info.control_type=='Hyperlink':
                try:
                    value=control.legacy_properties().get('Value','')
                    if isinstance(value,str) and value.startswith(('http://','https://')):item['href']=value[:2000]
                except Exception:pass
            elements.append(item);refs[ref]=control
        token=uuid.uuid4().hex
        selected_tabs=[tab['title'] for tab in tabs if tab['selected'] is True]
        self.snapshot={'id':token,'hwnd':hwnd,'at':time.monotonic(),'refs':refs}
        return {'id':token,'hwnd':hwnd,'title':window.window_text(),'selected_tab':'; '.join(selected_tabs) or None,'elements':elements,'background':True,'source':'Windows UI Automation','tab_count':len(tabs),'tabs':tabs,'controls_total':len(all_controls),'controls_truncated':len(elements)>=300,'note':'Controls are visible on the target window; offscreen controls are omitted. Tab labels identify tabs; inactive content and URLs are not verified. Select a tab and inspect again.'}
    async def act(self,args):
        return await asyncio.get_running_loop().run_in_executor(self.executor,self._act,args)
    def _act(self,args):
        obs=self.snapshot
        if not obs or obs['id']!=args['observation_id'] or time.monotonic()-obs['at']>90:raise ObservationError('Accessibility observation expired; inspect again')
        if bool(args.get('ref'))==bool(args.get('control_name')):
            raise ObservationError('Supply exactly one observed ref or exact control_name')
        if args.get('control_name'):
            matches=[control for control in obs['refs'].values() if control.element_info.name==args['control_name']]
            if len(matches)!=1:raise ObservationError('Control name is missing or ambiguous; inspect and use an exact ref')
            target=matches[0]
        else:target=obs['refs'].get(args['ref'])
        if target is None:raise ObservationError('Unknown accessibility reference')
        if target.element_info.element.CurrentIsPassword:raise ValueError('Enter account passwords yourself')
        if not target.is_enabled():raise ObservationError('Element is disabled')
        self.snapshot=None
        action=args['action']
        interface={'invoke':'iface_invoke','set_value':'iface_value','select':'iface_selection_item','toggle':'iface_toggle','scroll':'iface_scroll'}.get(action)
        if not interface:raise ValueError('Unknown accessibility action')
        try:pattern=getattr(target,interface)
        except Exception as exc:raise ObservationError('This control does not support direct '+action+'. Use a fresh screenshot and physical input in auto/physical mode, or another supported control.') from exc
        if action=='invoke':pattern.Invoke()
        elif action=='set_value':pattern.SetValue(args['text'])
        elif action=='select':pattern.Select()
        elif action=='toggle':pattern.Toggle()
        elif action=='scroll':pattern.Scroll(2,3 if args.get('amount',1)>0 else 0)
        verified=None
        if action in ('select','set_value'):
            for _ in range(10):
                try:verified=bool(target.iface_selection_item.CurrentIsSelected) if action=='select' else target.iface_value.CurrentValue==args['text']
                except Exception:verified=False
                if verified:break
                time.sleep(.1)
        try:after=self._inspect(obs['hwnd'])
        except Exception as exc:after={'hwnd':obs['hwnd'],'observation_unavailable':str(exc),'note':'Action was invoked; inspect again to verify. Do not repeat it blindly.'}
        return {'action':action,'background':True,'verified':verified,'verification_note':'Invocation alone does not prove task completion; inspect the resulting document/window.','after_accessibility':after}
