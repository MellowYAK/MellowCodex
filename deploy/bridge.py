"""Bootstrap a dedicated relay without modifying Ember's users or sites.

Run with Paramiko available. The password is prompted, never written to disk.
The SHA256 hex host-key pin is required and checked BEFORE authentication.
"""
import argparse, getpass, hashlib, json, os, shlex, subprocess, sys, time
from pathlib import Path
import paramiko


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',required=True)
    parser.add_argument('--host-key-sha256',required=True)
    parser.add_argument('--domain',required=True)
    parser.add_argument('--state',default='E:/AI/state')
    parser.add_argument('--password-stdin',action='store_true')
    args=parser.parse_args()
    import re
    if not re.fullmatch(r'[a-zA-Z0-9.-]+',args.domain):raise ValueError('Invalid domain')
    state=Path(args.state);home=state/'mcp';home.mkdir(parents=True,exist_ok=True)
    password=sys.stdin.readline().rstrip('\r\n') if args.password_stdin else getpass.getpass('SSH root password: ')
    transport=paramiko.Transport((args.host,22));transport.start_client(timeout=15)
    host_key=transport.get_remote_server_key()
    if hashlib.sha256(host_key.asbytes()).hexdigest()!=args.host_key_sha256:
        transport.close();raise RuntimeError('SSH host key differs from the pinned key')
    transport.auth_password('root',password);password=None
    client=paramiko.SSHClient();client._transport=transport
    sftp=client.open_sftp()

    def run(command,timeout=30):
        _,out,err=client.exec_command(command,timeout=timeout)
        text=out.read().decode();error=err.read().decode();code=out.channel.recv_exit_status()
        if code:raise RuntimeError(f'Remote command failed ({code}): {command}\n{error[-1500:]}')
        return text

    def write(path,text,mode=0o644):
        # Back up only this integration's files on a repeat deployment.
        try:sftp.stat(path)
        except FileNotFoundError:pass
        else:run('cp -- '+shlex.quote(path)+' '+shlex.quote(path+'.backup-'+str(int(time.time()))))
        with sftp.open(path,'w') as file:file.write(text)
        sftp.chmod(path,mode)

    protected='/etc/nginx/sites-available/ember-table /etc/nginx/sites-available/ember-video /etc/ssh/sshd_config.d/60-ember-tunnel.conf /home/ember-tunnel/.ssh/authorized_keys'
    before=run('sha256sum '+protected)
    (home/'ember-config-before.sha256').write_text(before)
    identity=home/'relay_key'
    if not identity.exists():paramiko.RSAKey.generate(3072).write_private_key_file(str(identity))
    key=paramiko.RSAKey.from_private_key_file(str(identity))
    known=home/'known_hosts';known.write_text(f'{args.host} {host_key.get_name()} {host_key.get_base64()}\n')
    if os.name=='nt':
        owner=subprocess.check_output(['whoami'],text=True).strip()
        subprocess.run(['icacls',str(home),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','SYSTEM:(OI)(CI)F'],check=True,capture_output=True)
        subprocess.run(['icacls',str(identity),'/inheritance:r','/grant:r',owner+':F','SYSTEM:F'],check=True,capture_output=True)
    user='local-agent-tunnel'
    run(f'id -u {user} >/dev/null 2>&1 || useradd --create-home --shell /usr/sbin/nologin {user}')
    run(f'install -d -m 700 -o {user} -g {user} /home/{user}/.ssh')
    write(f'/home/{user}/.ssh/authorized_keys',f'restrict,port-forwarding,permitlisten="127.0.0.1:18897" {key.get_name()} {key.get_base64()} local-agent-relay\n',0o600)
    run(f'chown {user}:{user} /home/{user}/.ssh/authorized_keys')
    write('/etc/ssh/sshd_config.d/61-local-agent-tunnel.conf',f'''Match User {user}
 PasswordAuthentication no
 PubkeyAuthentication yes
 AllowTcpForwarding remote
 PermitListen 127.0.0.1:18897
 AllowAgentForwarding no
 X11Forwarding no
 PermitTTY no
 GatewayPorts no
 ForceCommand /bin/false
Match all
''')
    run('sshd -t && systemctl reload ssh')
    domain=args.domain
    acme=f'''server {{ listen 80; server_name {domain};
 location ^~ /.well-known/acme-challenge/ {{ root /var/lib/letsencrypt; }}
 location / {{ return 301 https://$host$request_uri; }}
}}
'''
    site='/etc/nginx/sites-available/local-agent'
    write(site,acme)
    run('ln -sfn /etc/nginx/sites-available/local-agent /etc/nginx/sites-enabled/local-agent && nginx -t && systemctl reload nginx')
    print('SSH relay user and HTTP certificate challenge configured.',flush=True)
    run('/opt/ember-certbot/bin/certbot certonly --non-interactive --agree-tos --register-unsafely-without-email --webroot -w /var/lib/letsencrypt --cert-name local-agent -d '+shlex.quote(domain)+" --deploy-hook 'systemctl reload nginx'",timeout=120)
    write(site,acme+f'''server {{
 listen 443 ssl;
 server_name {domain};
 ssl_certificate /etc/letsencrypt/live/local-agent/fullchain.pem;
 ssl_certificate_key /etc/letsencrypt/live/local-agent/privkey.pem;
 ssl_protocols TLSv1.2 TLSv1.3;
 client_max_body_size 4m;
 access_log off;
 location / {{
  proxy_pass http://127.0.0.1:18897;
  proxy_http_version 1.1;
  proxy_set_header Host {domain};
  proxy_set_header X-Forwarded-Proto https;
  proxy_set_header X-Forwarded-For $remote_addr;
  proxy_buffering off;
  proxy_max_temp_file_size 0;
  proxy_read_timeout 120s;
 }}
}}
''')
    run('nginx -t && systemctl reload nginx')
    after=run('sha256sum '+protected)
    if before!=after:raise RuntimeError('An Ember configuration changed during deployment; inspect before proceeding')
    config={'enabled':True,'public_url':'https://'+domain,'relay_host':args.host,'relay_user':user,'relay_port':18897,'identity_file':str(identity.resolve()),'known_hosts':str(known.resolve())}
    (state/'relay.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (home/'deployment.json').write_text(json.dumps({'domain':domain,'time':time.time(),'ember_config_unchanged':True,'host_key_sha256':args.host_key_sha256},indent=2))
    client.close()
    print('TLS relay configured; Ember configuration hashes unchanged. Start Local Agent to connect.')


if __name__=='__main__':main()
