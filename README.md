## PYGPS Client

*pygps*
* Read Serial interface and grab data from the GPS receiver
* Calculate distance and speed between two successive reads
* Publish the data to a MQ (AMQP)

*pygps-consumer*
* Read the message published to MQ (AMQP)
* Enrich the message with context data
* POST the data to a remote API endpoint

### Hardware

Raspberry Pi Zero W  
[GSM/GPRS/GNSS/Bluetooth HAT for Raspberry Pi, Based on SIM868](https://www.waveshare.com/gsm-gprs-gnss-hat.htm)  
Huawei E3372


### CLIENT ENDPOINT

```
cat /etc/issue.net
Raspbian GNU/Linux 9
```

All the files are installed in /home/[SCRIPT]/pygps  
PYGPS will run as user [SCRIPT]

#### Prerequisites:

Packages: python3 (3.7.x), pip3, pip-tools, systemd, git, rabbitmq-server, memcached

As user root

```
cd /home/[SCRIPT]/pygps
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
pip-compile requirements.in -o requirements.txt
pip3 install -r requirements.txt
```

```
cd /etc/systemd/system/
```

**pygps.service**
```
[Unit]
Description=Python GPS Service
After=network.target memcached.service rabbitmq-server.service

[Service]
User=[SCRIPT]
Group=[SCRIPT]
Type=simple
ExecStart=/usr/bin/python3 /home/[SCRIPT]/pygps/pygps.py
Restart=always
RestartSec=3
StandardOutput=file:/var/log/pygps_stdout.log
StandardError=file:/var/log/pygps_stderr.log

[Install]
WantedBy=multi-user.target
Alias=pygps.service
```

**pygps-consumer.service**
```
[Unit]
Description=Python GPS consumer Service
After=network.target pygps.service

[Service]
User=[SCRIPT]
Group=[SCRIPT]
Type=simple
ExecStart=/usr/bin/python3 /home/[SCRIPT]/pygps/pygps-consumer.py
Restart=always
RestartSec=3
StandardOutput=file:/var/log/pygps-consumer_stdout.log
StandardError=file:/var/log/pygps-consumer_stderr.log

[Install]
WantedBy=multi-user.target
Alias=pygps-consumer.service
```

```
touch /var/log/pygps_stdout.log
touch /var/log/pygps_stderr.log
touch /var/log/pygps-consumer_stdout.log
touch /var/log/pygps-consumer_stderr.log
```

```
systemctl daemon-reload

systemctl start pygps.service
systemctl start pygps-consumer.service

journalctl -u pygps.service
journalctl -u pygps-consumer.service
```

**Log rotate**
```
cd /etc/logrotate.d/
```

**pygps**
```
/home/[SCRIPT]/pygps/logs/pygps-consumer.log
/home/[SCRIPT]/pygps/logs/pygps.log
/home/[SCRIPT]/pygps/cron/logs/getipaddress.log
{
	rotate 30
	maxsize 50M
	notifempty
	missingok
	nocreate
	daily
	compress
	delaycompress
}
```

As user [SCRIPT]

```
crontab -l
*/10 * * * * python3 /home/[SCRIPT]/pygps/cron/getipaddress.py
```

Change file access rights for the certificate files.
```
cd /home/[SCRIPT]/pygps/endpointpublish/certificates
chmod go-r *.pem
```

#### Install MemcacheDB

As root:
```
apt-get install memcached
update-rc.d memcached defaults
```

Configuration:
*/etc/memcached.conf*
```
-d
logfile /var/log/memcached.log
-m 64
-p 21201
-u memcache
-l 127.0.0.1
```

```
service memcached start
```

#### Install RabbitMQ (AMQP)

As root:
```
apt-get install rabbitmq-server -y
mkdir -p /etc/rabbitmq/ 
echo "[rabbitmq_management]." > /etc/rabbitmq/enabled_plugins
update-rc.d rabbitmq-server defaults
service rabbitmq-server start
```

##### RabbitMQ server definition

```
{
    "rabbit_version": "3.6.15",
    "users": [
        {
            "name": "admin",
            "password_hash": "cArRhHjba55meGIPRP7xZJdfvQ0Je1hqvbUWtqbwLezcnC41",
            "hashing_algorithm": "rabbit_password_hashing_sha256",
            "tags": "administrator"
        },
        {
            "name": "pygps",
            "password_hash": "YtZBOA1fvv8KAKhQNdCQvqu7fNk5no/bZIgeB2OkkAgP3aMi",
            "hashing_algorithm": "rabbit_password_hashing_sha256",
            "tags": ""
        }
    ],
    "vhosts": [
        {
            "name": "/"
        }
    ],
    "permissions": [
        {
            "user": "pygps",
            "vhost": "/",
            "configure": ".*",
            "write": ".*",
            "read": ".*"
        },
        {
            "user": "admin",
            "vhost": "/",
            "configure": ".*",
            "write": ".*",
            "read": ".*"
        }
    ],
    "parameters": [],
    "global_parameters": [
        {
            "name": "cluster_name",
            "value": "rabbit@raspberrypi"
        }
    ],
    "policies": [],
    "queues": [
        {
            "name": "GPSDetails",
            "vhost": "/",
            "durable": true,
            "auto_delete": false,
            "arguments": {
                "x-message-ttl": 432000000
            }
        }
    ],
    "exchanges": [],
    "bindings": []
}
```

#### Install Python3.7.x on Raspberry PI

As a non-root user:
```
cat /etc/issue.net
Raspbian GNU/Linux 9
pythonversion="3.7.5"
pythonversionmajor="3.7"
```


As root user:
```
apt-get install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev -y
```

As a non-root user:
```
cd /tmp
wget https://www.python.org/ftp/python/${pythonversion}/Python-${pythonversion}.tar.xz
tar xf Python-${pythonversion}.tar.xz

cd Python-${pythonversion}
./configure 
make -j 4
```

As root user:
```
make altinstall
```

*for root and the user script pygps*

As the respective user:
```
sed -i '/alias python3/d' ~/.bashrc
echo "alias python3=python${pythonversionmajor}" >> ~/.bashrc
source ~/.bashrc


cd /tmp
curl -O https://bootstrap.pypa.io/get-pip.py
```

As root user:
```
python3 get-pip.py
```

*for root and the user script pygps*

As the respective user:
```
sed -i '/alias pip3/d' ~/.bashrc
echo "alias pip3=pip${pythonversionmajor}" >> ~/.bashrc
source ~/.bashrc
```

##### Clean up

As root user:
```
cd /tmp
rm -fr Python-${pythonversion}
rm Python-${pythonversion}.tar.xz

apt-get --purge remove build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev -y
apt-get autoremove -y
apt-get clean
```
