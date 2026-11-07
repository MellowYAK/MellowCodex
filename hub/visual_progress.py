"""Block repeated input against an unchanged image, independently of the model."""
from PIL import Image, ImageChops, ImageStat
from .errors import ObservationError

class VisualProgress:
    def __init__(self):self.states={}
    @staticmethod
    def signature(args):
        return {k:v for k,v in args.items() if k!='observation_id'}
    @staticmethod
    def frame(path):
        with Image.open(path) as image:return image.convert('RGB').resize((256,160))
    def before(self,task_id,args,shot):
        state=self.states.get(task_id)
        if not state or state['count']<2 or state['action']!=self.signature(args):return
        try:current=self.frame(shot['path'])
        except (OSError,KeyError,TypeError):return
        if self.same(current,state['frame']):
            raise ObservationError('Repeated input made no visible progress. No input sent. Inspect the target with window_inspect, identify the active tab and blocking dialog, and use its observed control with window_act. Do not repeat the same coordinates or reopen the document.')
    @staticmethod
    def same(a,b):return max(ImageStat.Stat(ImageChops.difference(a,b)).mean)<0.3
    def after(self,task_id,args,before,after):
        try:a=self.frame(before['path']);b=self.frame(after['path'])
        except (OSError,KeyError,TypeError):return None
        unchanged=self.same(a,b);previous=self.states.get(task_id,{})
        signature=self.signature(args)
        count=(previous.get('count',0) if previous.get('action')==signature else 0)+1 if unchanged else 0
        self.states[task_id]={'count':count,'action':signature,'frame':b}
        return {'image_unchanged':unchanged,'unchanged_attempts':count,'note':'Input delivery is not task completion. Inspect controls/dialogs if unchanged; identical input is blocked after two unchanged attempts.'}
