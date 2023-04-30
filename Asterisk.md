# Configuração SIP no Asterisk 18

## Requisitos:

- Linux
- Docker


Neste tutorial, vamos configurar um servidor Asterisk 18 com as seguintes especificações:

- Número de telefone: 6001
- Senha: 6001
- Codec: G711u


### 1. Baixe o container docker mlan/asterisk

Antes de começar a configurar o servidor Asterisk, você precisa baixar o container que ele está instalado. Execute os comandos abaixo :

```
git clone https://github.com/mlan/docker-asterisk
```

Entre na pasta demo dentro do diretorio do projeto
```
cd docker-asterisk
cd demo
```

Execute o comando abaixo para executar o docker-compose e inciar o asterisk.

```
make up
```


Para entrar no container e fazer as proximas configurações:

```
docker exec -it demo_tele_1 bash
```

O comando acima entrará no terminal bash do container, isso possibilitará a configuração do servidor Asterisk. 

### 2. Configure as credenciais SIP

Agora, vamos configurar as credenciais SIP para o número de telefone 6001 e 6002.
Para efetuar uma ligação de uma conta para outra utilizando o servidor asterisk precisamos configurar duas contas.

Abra o arquivo `pjsip.conf` e adicione as seguintes linhas:

```
[6001]
type=endpoint
context=testing
disallow=all
allow=ulaw
auth=auth6002
aors=6002

[auth6001]
type=auth
auth_type=userpass
password=123456
username=6002

[6001]
type=aor
max_contacts=1


[6002]
type=endpoint
context=testing
disallow=all
allow=ulaw
auth=auth6002
aors=6002

[auth6002]
type=auth
auth_type=userpass
password=123456
username=6002

[6002]
type=aor
max_contacts=1
```


- `type=endpoint`: Define o tipo de endpoint, neste caso, SIP.
- `context=testing`: Define o contexto do endpoint, ou seja, o conjunto de regras de discagem que serão aplicadas quando uma chamada for feita para este endpoint.
- `disallow=all`: Desabilita todos os codecs.
- `allow=ulaw`: Habilita o codec G711u.
- `auth=auth6001`: Define a autenticação que será usada para este endpoint.
- `aors=6001`: Define o objeto AOR que será usado para este endpoint.

### 3. Reinicie o Asterisk

Depois de salvar as alterações no arquivo `pjsip.conf`, reinicie o servidor Asterisk para que as mudanças tenham efeito.

### 4. Faça uma chamada de teste

Com o servidor configurado e em execução, abra o Zoiper ou qualquer outro aplicativo de softphone e crie uma conta SIP usando as seguintes credenciais:

- Nome de usuário: 6001
- Senha: 6001
- Endereço SIP: IP_do_servidor_asterisk

E em outro zoiper:

- Nome de usuário: 6002
- Senha: 6002
- Endereço SIP: IP_do_servidor_asterisk

Certifique-se que os dispositivos com o Zoiper instalado estão na rede e com o ip correto do servidor Asterisk.

Depois de criar a conta SIP, você pode fazer uma chamada de teste para qualquer número de telefone cadastrado no servidor Asterisk. Para fazer ligações para numeros externos você precisa cadastrar um provedor de serviços VoIP.