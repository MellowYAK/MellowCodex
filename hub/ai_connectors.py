"""Product connection catalog; availability is not authenticated connection state."""


def catalog():
    result = {'items':[
        {'id':'chatgpt','name':'ChatGPT','mark':'GPT','description':'שיחות, התייעצות וביצוע משימות דרך הסוכן המקומי.',
         'transports':[{'id':'play','name':'Web PLAY','implemented':True,'requires':'שיחת ChatGPT מחוברת בדפדפן הסוכן'},
                       {'id':'mcp','name':'MCP','implemented':True,'requires':'מחבר MCP מאומת והרשאה לסוכן'}],
         'connection_state':'not_checked'},
        {'id':'claude','name':'Claude','mark':'C','description':'חיבור שיחה דרך Web PLAY מתוכנן. המתאם עדיין אינו פעיל.',
         'transports':[{'id':'play','name':'Web PLAY','implemented':False,'requires':'מתאם ספק ובדיקת התחברות'}],
         'connection_state':'not_implemented'},
        {'id':'deepseek','name':'DeepSeek','mark':'D','description':'חיבור שיחה דרך Web PLAY מתוכנן. המתאם עדיין אינו פעיל.',
         'transports':[{'id':'play','name':'Web PLAY','implemented':False,'requires':'מתאם ספק ובדיקת התחברות'}],
         'connection_state':'not_implemented'},
    ],'note':'PLAY names the browser-chat transport. A catalog card is not proof of authentication or task execution.'}

    from .i18n import t
    from .remote_config import PUBLIC
    for item in result['items']:
        if item['id'] != 'chatgpt':
            item['description'] = t('connectors.mcp_description', 'he')
            item['transports'].append({'id':'mcp','name':'MCP','implemented':True,
                                       'requires':t('connectors.mcp_requirement','he')})
            item['connection_state']='not_checked'
    result['items'].append({'id':'custom','name':t('connectors.other','he'),'mark':'AI',
        'description':t('connectors.mcp_description','he'),'connection_state':'not_checked',
        'transports':[{'id':'mcp','name':'MCP','implemented':True,'requires':t('connectors.mcp_requirement','he')}]})
    result['mcp']={'url':PUBLIC+'/mcp','authentication':'OAuth','labels':{
        key:t('connectors.'+key,'he') for key in ('setup','instructions','approve','status_note')}}
    return result
