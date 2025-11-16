# **ETAIL LINUX HELPERS**

_________________________________________________________________

Set of utils to send data to the server of ETail.

SSL is default for all.

Each one has a set of scripts for environment run, compiling and installing.

The releases section has an installer for the compiled scripts (recomended) ready to use in AMD x64 Linux.

Common parameters for all the apps.

* Name: To identify the monitor.
* Host: ip or name where the info will be seent. default localhost
* Port: the server port to send. default 21327
* Password: password to comunicate
* Run at start: Run the process when you launch the app.
* Poll interval: default 5 s.

The releases dir have the executables needed and a installer for them. It's recomended to use them, sources will need several environment installs.

It's recomended to install lm-sensors in your system if you don't have it installed. "sudo apt install lm-sensors"

The usage guide refers to the binary versions.

### **Etail Monitor Controller**

/usr/local/bin/etail-monitor-controller
Configs in ~/.config/etail-monitor-controller

* Name: To identify the monitor.
* Host: ip or name where the info will be seent. default localhost
* Port: the server port to send. default 21327
* Password: password to comunicate
* Run at start: Run the process when you launch the app.
* Poll interval: default 5 s.


Organizer for the helpers.

You can add, edit, delete and control the execution of the helpers.

This app can monitor the processes that share the helpers name. Also you can control the processes and services that YOU create in the corresponding tabs. After a reboot you could loose the control of the services, but you can manage them elsewhere.

The app tries to track duplicates and prevent them to run, but only the managed ones.

Each tab manages a type of lauch, service, which will need you to run as root and processes, some of them would need to be ran as root too dependig on what are you tracking.

Launchs executable version of the helpers. This is because this way dependencies or python installing will not be necesary (or so it says the documentation of pyisntaller). You can compile the source using the scripts in the Linux Helpers dir corresponding of each app.

Helpers can be launch as console applications. A readme in their source dir explains how to use and install them.

#### **Managed Services**

Here you can Add, Edit and control services created by the app. Note that restarts can change the PID and you could lose control from app.

Root privileges are needed to control these services.

* Display Name: Name to identify the service.
* Systemd Service Name: the name you give to the system in order to control the service.
* Executable path: Location of the executable to run.
* Service type:
	1. options are hardware_monitor (et_hardware_mon_linux)
	2. log_monitor(LinuxLogMonitor) It has an text fiel to add several logs separaterd by commas.
	3. custom. You can select some executable to make a service from it.
	

#### **Managed Processes**

Here you can Add, Edit and control processes created by the app. Note that restarts can change the PID and you could lose control from app.

The main diference with the services is that these don't restart after a reboot. But you can check "Auto Start with Controller" to start them when opening the app.
	

#### **System View**

A list to see what helpers are active, also the otrhe processes you have launched. Processes whose owner is "root" sould be services.

#### **Process Trees**

Here are shown the relations between the active processes.

## **ETail Hardware Monitor**

/usr/local/bin/et_hardware_mon_linux

A console application to send hardware metris to a log monitor server.

usage: et_hardware_mon_linux [-h] [--host HOST] [--port PORT] --password PASSWORD [--refresh-interval REFRESH_INTERVAL] [--no-ssl]


## **ETail Log Monitor**


/usr/local/bin/LinuxLogMonitor

usage: LinuxLogMonitor [-h] [--host HOST] [--port PORT] [--password PASSWORD] [--log-files LOG_FILES [LOG_FILES ...]] [--no-ssl]
                       [--poll-interval POLL_INTERVAL] [--tail-lines TAIL_LINES] [--encoding ENCODING] [--drop-privileges]
                       [--run-as-user RUN_AS_USER] [--config CONFIG] [--create-sample-config]


## **ETail Panel Applet**

/usr/local/bin/etail-panel-applet

Applet that shows number of etail processes active and configured. Also youi can invoke the controller clickin on it's icon. Red is none active, yellow some, green all.

TODO.

Clean code and bugs. Improve GUI. Remake the applet in C.