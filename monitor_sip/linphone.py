# -*- coding: utf-8 -*-
import os
import time
import subprocess as sp

"""
Classe do linphone
"""
class Linphone:

    """
    Init da classe, invoca o método start() para criação do daemon do Linphone
    """
    def __init__(self):
        self.state = False
        self.isRegistered = False
        try:
            self.start()
        except OSError:
            print ("E: Cant spin up the daemon")
            exit()
    """
    Método que inicia o linphonecsh e faz a configuração de auto atendimento e configura as interfaces de áudio da raspberry
    """
    def start(self):
        if(not os.system("linphonecsh init")):
            print ("Daemon inited")
        else:
            raise OSError
        time.sleep(0.5)
        self.enable_autoanswer()
        time.sleep(0.5)
        self.use_bcm_card()
    
    """
    Método que verifica se o client sip está registrado
    :return: True se é registrado e False se não está registrado.
    """
    #Não está funcioando, por algum moitvo o linphonesch não está retornando o status correto de registro
    def check_register(self):
        output = sp.getoutput('linphonecsh status register')
        #if( output == "registered=-1" or output == "registered=0"):
        if(output == "registered=0"):
            self.isRegistered = False
            return False
        else:
            self.isRegistered = True
            return True

    """
    Método que força o registro do linphonecsh daemon
    :return: Retorna True se está registrado e false se não registrou
    """
    #Testar com subprocess subprocess.call(["ipconfig"])
    def register(self,host,username,password):
        try:
            host1 = host
            username1 = username
            password1 = password
            if(not os.system("linphonecsh register --host "+str(host1)+" --username "+str(username1)+" --password "+str(password1)+"")):
                if self.check_register():
                    self.isRegistered = True
                    print  ("I: Registrado")
                    return True
                else:
                    self.isRegistered = False
                    print("I: Não Registrado")
        except:
            self.isRegistered = False
            print ("Except: Falha no registro")
            return False

    """
    Método para habilitar o atendimento automatico do sip client
    :return: True se foi aplicado o comando de habilitar o Autoanswer, false se tiver uma falha
    """
    def enable_autoanswer(self):
        try:
            if(not os.system("linphonecsh generic 'autoanswer enable'")):
                return True
            else:
                return False
        except:
            return False

    """
    Método que configura os periféricos de áudio da raspberry
    :return: retorna true se foi configurado as interfaces de audio com sucesso ou false se acontecer algum erro na execução
    """
    def use_bcm_card(self):
        try:
            if(not os.system("linphonecsh generic 'soundcard ring 2'")):
                if(not os.system("linphonecsh generic 'soundcard capture 3'")):
                    if(not os.system("linphonecsh generic 'soundcard playback 2'")):
                        return True
        except:
            print("Exception: configuração de soundcard")
            return False
    """
    Método que para o Daemon do linphone previamente instanciado
    """
    def stop(self):
        try:
            if(not os.system("linphonecsh exit")):
                return True
        except:
            print("Exception: linphonecsh exit")
            return False

    """
    __del__ invoca o método stop() para fechar o objeto linphonecsh previamente instanciado, isso é executado quando é descartado o objeto da classe Linphone por algum motivo
    """
    def __del__(self):
        self.stop