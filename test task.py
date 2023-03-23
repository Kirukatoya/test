import paramiko
import psycopg2
import subprocess

# Параметры серверов
SERVER_A = '10.0.0.1'
SERVER_B = '10.0.0.2'
SERVER_C = '10.0.0.3'
SSH_USERNAME = 'US'
SSH_PASSWORD = 'abc123'

developer_user = "developer"


# Отключение авторизации SSH по паролю на сервере B:
def disable_password_auth_on_server_b():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_B, username=SSH_USERNAME, password=SSH_PASSWORD)

    # Отключение авторизации по паролю
    ssh.exec_command('sudo sed -i "s/#PasswordAuthentication yes/PasswordAuthentication no/g" /etc/ssh/sshd_config')
    ssh.exec_command('sudo service ssh restart')
    ssh.close()


# Добавление пользователя DevOps на сервер B и настройка авторизации по ключам:
def add_user_and_setup_key_auth_on_server_b():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_B, username=SSH_USERNAME, password=SSH_PASSWORD)

    # Добавление пользователя DevOps
    ssh.exec_command('sudo adduser devops')

    # Настройка авторизации по ключам
    ssh.exec_command('sudo mkdir -p /home/devops/.ssh')
    ssh.exec_command('sudo chmod 700 /home/devops/.ssh')
    ssh.exec_command('sudo touch /home/devops/.ssh/authorized_keys')
    ssh.exec_command('sudo chmod 600 /home/devops/.ssh/authorized_keys')

    # Скопировать публичный ключ пользователя на сервер B
    with open('/path/to/public/key.pub', 'r') as pubkey_file: pubkey = pubkey_file.read().strip()
    ssh.exec_command(f'sudo echo "{pubkey}" >> /home/devops/.ssh/authorized_keys')

    # Дать права sudo пользователю DevOps
    ssh.exec_command('sudo usermod -aG sudo devops')
    ssh.close()


# Установка PostgreSQL и настройка доступа на сервере B:
def install_postgres_and_setup_access_on_server_b():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_B, username=SSH_USERNAME, password=SSH_PASSWORD)

    # Установка PostgreSQL
    ssh.exec_command('sudo apt-get update')
    ssh.exec_command('sudo apt-get install postgresql postgresql-contrib -y')

    # Создать пользователя developer
    ssh.exec_command('sudo adduser developer')

    conn = psycopg2.connect(dbname="postgres", user="developer", password="abc123", host="10.0.0.2")
    cursor = conn.cursor()

    conn.autocommit = True

    # команда для создания базы данных myapp и myauth
    sql = "CREATE DATABASE myapp"

    # выполняем код sql
    cursor.execute(sql)

    sql = "CREATE DATABASE myauth"
    cursor.execute(sql)
    print("Базы данных успешно созданы")

    cursor.close()
    conn.close()

    # Назначить права на запись и чтение для пользователя developer
    ssh.exec_command("sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE myapp TO {}\"".format(developer_user))

    # Назначить права на чтение для пользователя developer
    ssh.exec_command("sudo -u postgres psql -c \"GRANT SELECT ON DATABASE myauth TO {}\"".format(developer_user))

# Настроить доступ пользователя developer только с сервера C
#Добавление правила фаервола на сервере B для доступа к PostgreSQL только с сервера C
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=SERVER_B, username='root', password='<root_password>')
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo apt-get update && sudo apt-get install -y ufw')
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo ufw allow from {} to any port 5432'.format(SERVER_C))
ssh.close()

#Настройка доступа к PostgreSQL только с сервера C
ssh.exec_command('sudo -u postgres psql -c "REVOKE CONNECT ON DATABASE myapp FROM PUBLIC"')
ssh.exec_command('sudo -u postgres psql -c "REVOKE CONNECT ON DATABASE myauth FROM PUBLIC"')
ssh.exec_command( "sudo -u postgres psql -c \"GRANT CONNECT ON DATABASE myapp TO {}\"".format(developer_user))
ssh.exec_command( "sudo -u postgres psql -c \"GRANT CONNECT ON DATABASE myauth TO {}\"".format(developer_user))
ssh.exec_command( "sudo -u postgres psql -c \"ALTER DATABASE myapp OWNER TO {}\"".format(developer_user))
ssh.exec_command( "sudo -u postgres psql -c \"ALTER DATABASE myauth OWNER TO {}\"".format(developer_user))
# Настроить доступ к PostgreSQL только с сервера C
ssh.exec_command( "sudo sed -i 's/#listen_addresses = '\''localhost'\''/listen_addresses = '\''*'\''/g' /etc/postgresql/13/main/postgresql.conf")
ssh.exec_command( "sudo bash -c 'echo \"host all all 10.0.0.3/32 md5\" >> /etc/postgresql/13/main/pg_hba.conf'")
ssh.exec_command( "sudo service postgresql restart")

#Проверка доступа к PostgreSQL на сервере C под пользователем developer
conn = psycopg2.connect(host=SERVER_C, port='5432', dbname='myauth', user='developer', password='developer')
cur = conn.cursor()
cur.execute('SELECT * FROM <table>;')
result = cur.fetchall()
print(result)
cur.close()
conn.close()

#Запрещаем доступ к серверам B и C с любых других адресов, кроме сервера A

ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo ufw default deny incoming')
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo ufw allow from {} to any port 22'.format(SERVER_A))
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo ufw enable')
ssh.close()

#Проверка доступа к серверам B и C только с сервера A

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=SERVER_A, username='root', password='<root_password>')
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('ssh root@{} echo "Access to server B from server A is working"'.format(SERVER_B))
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('ssh root@{} echo "Access to server C from server A is working"'.format(SERVER_C))
print(ssh_stdout.read().decode())
ssh.close()
