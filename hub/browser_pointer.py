"""Schemas for existing embedded-browser virtual input, not OS input."""
from .i18n import t

def register_mcp(mcp,local,read,write):
    from mcp.types import CallToolResult,TextContent,ImageContent
    import json
    from typing import Literal
    @mcp.tool(description=t('browser.frame_tool'),annotations=read)
    async def browser_frame():
        result=await local('/api/browser/frame')
        image=result.pop('image')
        return CallToolResult(content=[TextContent(type='text',text=json.dumps(result,ensure_ascii=False)),ImageContent(type='image',mimeType='image/jpeg',data=image.split(',',1)[1])])
    @mcp.tool(description=t('browser.pointer_tool'),annotations=write)
    async def browser_pointer(frame_id:str,action:Literal['move','click','drag','scroll'],x:float=0,y:float=0,end_x:float=0,end_y:float=0,amount:int=0,button:Literal['left','right','middle']='left',ref:str='',end_ref:str=''):
        return await local('/api/browser/input',dict(frame_id=frame_id,action=action,x=x,y=y,end_x=end_x,end_y=end_y,amount=amount,button=button,ref=ref,end_ref=end_ref))

def definitions(schema):
    number={'type':'number'}
    return [schema('browser_frame',t('browser.frame_tool'),{}),schema('browser_pointer',t('browser.pointer_tool'),{
        'frame_id':{'type':'string'},'action':{'type':'string','enum':['move','click','drag','scroll']},
        'ref':{'type':'string'},'end_ref':{'type':'string'},
        'x':number,'y':number,'end_x':number,'end_y':number,'amount':{'type':'integer'},'button':{'type':'string','enum':['left','right','middle']}},('frame_id','action'))]
