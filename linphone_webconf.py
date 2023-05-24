# -*- coding: utf-8 -*-
#!/usr/bin/env python3
from __future__ import with_statement
from contextlib import closing
from threading import Thread
from updateLinphonerc import UpdateLinphonerc
from updateExtensionTo import UpdateExtensionTo
from showDevices import ShowDevices
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
import os
from linphone import Linphone
import ipaddress
import hashlib
import netifaces
import netifaces as ni
import dns.resolver
from netifaces import AF_INET, AF_INET6, AF_LINK, AF_PACKET, AF_BRIDGE
import logging
import subprocess
  
DATABASE = 'phones.db'
DEBUG = False
SECRET_KEY = 'admin'
DEFAULTUSERNAME = 'admin'
DEFAULTPASSWORD  = 'admin'
HOST = '0.0.0.0'
PORT = 8081
dataschema = 'schema.sql'
app = Flask(__name__)
app.config.from_object(__name__)
print("Init")
phone = Linphone()
updateall = UpdateLinphonerc()
devicesClass = ShowDevices()
update_extension_to = UpdateExtensionTo()
LOGSPATH = '/usr/local/sbin/linphone-webconf/log_linphone-webconf.log'
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True


"""
Tabela de chaves para alterar o s parametros do .linphonerc
"""
keyword = {
    'contact' : 'contact=',
    'reg_proxy' : 'reg_proxy=',
    'reg_identity' : 'reg_identity=',
    'username' : 'username=',
    'realm' : 'realm=',
    'domain' : 'domain='
}

"""
Conecta com o banco de dados 'phones.db'
:rertun: Retorna a conexão com o banco
"""
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

"""
Inicia o banco SQL com as credênciais necessárias
"""
def init_db():
    with closing(connect_db()) as db:
        with app.open_resource(dataschema) as schema:
            db.cursor().executescript(schema.read())
            setauth(db,app.config['DEFAULTUSERNAME'],app.config['DEFAULTPASSWORD'])
        db.commit()

"""
Compara as credenciais de acesso dado de entrada no método com o que há previamente configurado no banco de dados.
:param user: Usuário para tentativa de acesso
:param password: Senha para tentativa de acesso
:return: True se as credenciais passadas por parametro se encontra no banco de dados e False se a senha ou usuário é incorreto
"""
def auth(user,password):
    try:
        cur = g.db.execute('select username, password from auth')
    except Exception as e:
        logger.error('Connection with DB failed')
    for row  in cur:
        db_user = row[0]
        db_pass = row[1]
        if (user == db_user) and (password == db_pass):
            logger.info('Connection Authentication accepted -> '+'User:'+ user + ' Password:'+ password)
            return True
        else:
            logger.error('Connection Authentication Refused -> '+'User:'+ user + ' Password:'+ password)
            return False

"""
Método para definir usuário e senha de acesso a interface web do produto
:param db: banco de dados para definir a senha
:param user: Usuário a ser alterado no banco de dados (db)
:param password: Senha a ser alterada no banco de dados (db)
"""
def setauth(db,user,password):
    try:
       # pashash = hashlib.md5(password.encode())
        db.execute("delete from auth")
        #db.execute("insert into auth (username, password) values('{0}', '{1}')".format(user,pashash.hexdigest()))
        db.execute("insert into auth (username, password) values('{0}', '{1}')".format(user,password))
        db.commit()
        logger.info('Set Authentication accepted -> '+'User:'+ user + ' Password:'+ password)
        return True
    except TypeError:
        logger.error('Change Authentication Failed')
        return False

"""
Método para registar o client SIP, dado como entrada o bando de dados onde possui as credenciais de registro SIP.
:param db: bando de dados que a função irá consultar as credenciais de registro SIP. (obs: Atualmente só um client SIP é alocado no banco, poderiamos expandir isso facilmente)
"""
def register(db):
    try:
        cur = db.execute('select username, server,password from entries order by id')
        for row in cur.fetchall():
            username=row[0]
            server=row[1]
            password=row[2]
            phone.register(server,username,password)
        logger.info('Registered OK -> Peer '+ username + 'registered with successful on PABX: '+ server)
        return True
    except TypeError:
        logger.error('Register failed')
        return False


"""
Método executado antes de cada solicitação feita, ou seja, antes de qualquer requisição é realizada a conexão do banco de dados
"""
@app.before_request
def before_request():
    g.db = connect_db()

"""
Método executado ao final de cada solicitação, bem sucedida ou uma exceção. Neste caso ele fechará o banco após cada requisição.
"""
@app.teardown_request
def teardown_request(exception):
    g.db.close()

"""
Método para redirecionar para a url de login
:return: redireciona para a URL de login
"""
@app.route('/')
def show_entries():
    return redirect(url_for('login'))

"""
Método onde renderiza a interface login.html caso seja dado um GET na URL /login. Se for aplica um POST ele irá tentar fazer o login na interface web do  produto através do username e password
:return: Retorna a interface login.html caso seja dado um GET na URL /login ou se o usuário errar a senha da interface web. Renderiza o menu.html se o POST de login for realizado com sucesso.
"""
@app.route('/login', methods=['GET','POST'])
def login():
    
    if request.method == 'POST':
        if not auth(request.form['username'], request.form['password']):   
            flash('Falha no login!') 
        else:
            session['logged_in'] = True
            return render_template('menu.html')
    return render_template('login.html')

"""
Rota para a url /network.html, caso é dado um GET na página ela retornar o método read_network(método que renderiza a pagina de configurações de rede com os dados incluso no banco de dados). 
Caso seja um POST (aplicou a configuração na interface web), é invocado o método change_network() que faz a alteração das configurações de rede, após a atualização das configurações de rede no banco é renderizado a interface web no menu de rede novamente.
"""
@app.route('/network.html',methods=['GET','POST'])
def network(): 
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        ipaddr = request.form['ipaddr']
        mask = request.form['mask']
        gateway = request.form['gateway']
        dns = request.form['dns']
        change_network(ipaddr,mask,gateway,dns)
        return read_network()
    return read_network()

"""
Método para alterar as configurações de rede da placa
:param ipaddr: Novo endereço IP para placa
:param mask: Nova máscada de rede para a placa
:param gateway: Novo endereço de gateway para placa
:param dns: Novo endereço de DNS para placa
:return: True se foi possível alterar as configurações de rede e false se acontecer algum erro
"""
# tirar essdes if tudo e deixa somente o os.system para testar. se der alguma exceção será tratado automaticamente
def change_network(ipaddr,mask,gateway,dns):
    try:
        if(validate_ip_address(ipaddr)):
            ipaddr1 = ipaddr
        if(validate_ip_address(mask)):
            mask1 = mask
        if(validate_ip_address(gateway)):
            gateway1 = gateway
        dns1 = dns
        if(not os.system('echo "auto lo" > /etc/network/interfaces')):
            logger.info('Added auto lo on /etc/network/interfaces')
        if(not os.system('echo "iface lo inet loopback" >> /etc/network/interfaces')):
            logger.info('Added iface lo inet loopback on /etc/network/interfaces')
        if (not os.system('echo "auto eth0" >> /etc/network/interfaces')):
            logger.info('Added auto eth0 on /etc/network/interfaces')
        if (not os.system('echo "iface eth0 inet static" >> /etc/network/interfaces')):
            logger.info("Added iface eth0 inet static on /etc/network/interfaces")
        if (not os.system('echo "address "'+ipaddr1+' >> /etc/network/interfaces')):
            logger.info("Changed IP Addres to: "+ipaddr1)
        if (not os.system('echo "netmask "'+mask1+' >> /etc/network/interfaces')):
            logger.info("Changed Mask to: "+mask1)
        if (not os.system('echo "gateway "'+gateway1+' >> /etc/network/interfaces')):
            logger.info("Changed Gateway to: "+gateway1)
        if (not os.system('echo "dns-nameservers "'+dns1+' >> /etc/network/interfaces')):
            logger.info("Configured DNS on interfaces: "+dns1)
        if (not os.system("chattr -a /etc/resolv.conf")):
            logger.info('resolv.conf desbloqueado cin chattr -a')
        if (not os.system('echo "nameserver "'+dns1+' > /etc/resolv.conf')):
            logger.info("Configured DNS on resolv.conf: "+dns1)
        if (not os.system("chattr +a /etc/resolv.conf")):
            logger.info("resolv.conf bloqueado")
        if (not os.system("sudo ifdown eth0")):
            logger.info("IFDOWN OK")
        if (not os.system("sudo ifup eth0")):
            logger.info("IFUP OK")
        if (not os.system("sudo /etc/init.d/networking restart")):
            logger.info("Networking restart")
        if (not os.system("sudo ifup eth0")):
            logger.info("IFUP OK")
        logger.info('NEW NETWORK CONFIGURATION OK')
        return True
    except:
        logger.error('Change network failed')
        return False

    """
    Método que verifica as configurações de rede atual da placa.
    :return: Renderiza o menu de rede network.html com as configurações atuais da placa 
    """
def read_network():
    ip = ni.ifaddresses('eth0')[AF_INET][0]['addr']
    print(ip)
    netmask = ni.ifaddresses('eth0')[AF_INET][0]['netmask']
    print(netmask)
    gws = netifaces.gateways()
    gateway = gws['default'][netifaces.AF_INET][0]
    print(gateway)
    dns_resolver = dns.resolver.Resolver()
    dns1 = dns_resolver.nameservers[0] 
    print(dns1)
    return render_template('network.html',ip=ip,netmask=netmask,gateway=gateway,dns=dns1)

"""
Rota para renderizar o menu principal de configuração
"""
@app.route('/menu.html')
def menu():
    if not session.get('logged_in'):
        abort(401)
    return render_template('menu.html')

"""
Rota para o password.html, neste método quando é dado um GET ness URL é renderizado o menu de troca de password.
Se for um POST (Salvar na interface web), o método irá capturar o que foi escrito nos campos e invocar o método changepassword(username, password, rpassword) para alterar as credenciais de acesso a interface web.
"""
@app.route('/password.html',methods=['GET','POST'])
def password():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rpassword = request.form['rpassword']
        changepassword(username,password,rpassword)
        return render_template('password.html')
    return render_template('password.html')

"""
Rota para renderizar o menu áudio
"""
@app.route('/Audio.html')
def Audio():
    if not session.get('logged_in'):
        abort(401)
    return render_template('Audio.html')

"""
Rota para interface de configuração SIP. Caso for um POST o método irá atualizar o banco de dados com as novas informações SIP do dispositivo. Se for um GET irá ser invocado o método  read_sip() para renderizar na interface web os valores atuais da configuração SIP do dispositivo.
"""
@app.route('/SIP.html',methods=['GET','POST'])
def SIP():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        title = request.form['title']
        username = request.form['username']
        server = request.form['server']
        password = request.form['password']
        queryy = "UPDATE entries SET title=? ,username=?,password=?,server=? where id = 1"
        g.db.execute(queryy,(title,username,password,server,))
        g.db.commit()
        phone.stop()
        phone.start() 
        updateall.update_file(keyword['contact'],username+'@'+server) 
        updateall.update_file(keyword['realm'],server) 
        updateall.update_file(keyword['reg_proxy'],'sip:'+server) 
        updateall.update_file(keyword['reg_identity'],'sip:'+username+'@'+server) 
        updateall.update_file(keyword['username'],username) 
        updateall.update_file(keyword['domain'],server) 
        update_extension_to.updateExtensionCall(server,title)
        register(g.db)     
        return read_sip()
    else:
        #phone.start() 
        return read_sip()

   

"""
Método que verifica no banco de dados as configurações atuais SIP e renderiza a interface web com esses parametros.
"""
def read_sip():
    cur = g.db.execute('select username, server,password,title from entries order by id')
    status = ck_register()
    for row in cur.fetchall():
        username=row[0]
        server=row[1]
        password=row[2]
        title=row[3]
    return render_template('SIP.html',username=username,password=password,server=server,title=title,status=status)
 
 
"""
Método para mudar a senha de acesso web
"""
def changepassword(username,password,rpassword):
    error = None
    if len(username) == 0:
        error = "Usuario vazio"
        logger.error("User is empty")
    elif password == rpassword:
        error = 'Mesma senha'
        logger.warning("The new password is the same that old passsword")
    else:
        setauth(g.db,username,rpassword)
        logger.info("New password was accepted!")
    return render_template('password.html', error=error)

"""
Método que verifica se o client SIP está online ou não
:return: Retorna uma String informando se ta registrado ou não
"""
def ck_register():
    if (phone.check_register()):
        registrado = "Registrado!"
    else:
        registrado = "Não_está_registrado"
    return registrado

"""
Método para rebootar o dispositivo
"""
@app.route('/reboot',methods=['GET','POST'])
def reboot():
    logger.warning('Rebooting device')
    os.system("reboot -f")

"""
Método força o registro SIP e renderiza o menu principal de configuração
"""
@app.route('/Salvar')
def Salvar():
    flash('Salvo com sucesso')
    phone.stop()
    phone.start() #failed to conect pipe; no sush file or directory
    register(g.db)
    return render_template('menu.html')

"""
Método que desloga da interface web e retorna para a página de login
"""
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


"""
Método que faz a verificação se o endereço IP digitado é um endereço válido
"""
def validate_ip_address(address):
    try:
        ip = ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


@app.route('/devicesRegistered.html',methods=['GET','POST'])
def read_devices():
    if request.method =='POST':
        if request.form['submit_button'] == 'Abrir Rede Zigbee':
            cmd_openZigbee = '/usr/bin/mosquitto_pub -h mqtt.tago.io -p 1883 -u andrey -P "dbd6ad7e-9e15-4d91-9d8f-d5720e568d73" -t IPHEALTH/bridge/request/permit_join -m "{\\"device\\":null,\\"time\\":254,\\"transaction\\":\\"5b6r3-1\\",\\"value\\":true}"'
            os.system(cmd_openZigbee)
            print("Abre a rede demonho!!!!!!!!!")
            return devicesClass.read_devices()
        elif request.form['submit_button'] == 'Fechar Rede Zigbee':
            cmd_closeZigbee = '/usr/bin/mosquitto_pub -h mqtt.tago.io -p 1883 -u andrey -P "dbd6ad7e-9e15-4d91-9d8f-d5720e568d73" -t IPHEALTH/bridge/request/permit_join -m "{\\"device\\":null,\\"time\\":254,\\"transaction\\":\\"5b6r3-1\\",\\"value\\":false}"'
            os.system(cmd_closeZigbee)
            print("Fechando a rede demonho!!!!!!!!!")
            return devicesClass.read_devices()

        elif request.form['submit_button'] == 'Atualizar':
            return devicesClass.read_devices()

    elif request.method == 'GET':
        return devicesClass.read_devices()

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=LOGSPATH, filemode='a', format='%(asctime)s : %(name)s : %(levelname)s : %(message)s', level=logging.DEBUG)
    ctx = app.app_context()
    ctx.push()
    if not os.path.isfile(app.config['DATABASE']):
        init_db()
    before_request()
    phone.stop()
    phone.start()
    register(g.db)

    app.run(app.config.get('HOST'), app.config.get('PORT'))

