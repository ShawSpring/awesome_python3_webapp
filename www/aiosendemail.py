import asyncio
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
from email.header import Header
import aiosmtplib
import logging
def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), addr))

from_addr = 'chunlaixiao@163.com'
password = 'aXiaoyx2@_'
to_addr = '745899213@qq.com'
smtp_server = "smtp.163.com"
link = "http:www.baidu.com"

async def sendemail(to_addr,link):
    title = '<html><body><h3>亲爱的<a data-auto-link="1" href="mailto:%s" target="_blank">%s</a>,您好:</h3>'%(to_addr,to_addr)
    reset = "<div style = 'padding-left:55px;padding-right:55px;font-family:'微软雅黑','黑体',arial;font-size:14px;'>重置密码</div>"
    body = '<p>请点击以下链接进行重置密码 <a href="%s">%s</a></p>'%(link,reset)
    tail = '如果您并不是Awesome用户，可能是其他用户误输入了您的邮箱地址。</body></html>'
    html = title+body+tail

    msg = MIMEText(html, 'html', 'utf-8')
    msg['From'] = _format_addr('Awesome Python Webapp <%s>' % from_addr)
    msg['To'] = _format_addr('亲爱的用户 <%s>' % to_addr)
    msg['Subject'] = Header('重置密码', 'utf-8').encode()
    try:
        async with aiosmtplib.SMTP(hostname=smtp_server,port=465,use_tls=True) as smtp:
            await smtp.login(from_addr,password)
            await smtp.send_message(msg)
    except aiosmtplib.SMTPException as e:
        logging.error('sendemail:%s'%e)
        
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sendemail(to_addr,link))