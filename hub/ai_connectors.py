"""Product connection catalog; availability is not authenticated connection state."""


def catalog():
    return {'items':[
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
