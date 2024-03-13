# HouseBlend

Simple Blender rendering using your home network.

## Instructions

### On your workstation
```
$ pip install git+https://github.com/tf198/houseblend.git

# change into whatever directory contains your working blendfiles
$ cd projects

# run the manager
$ houseblend-manager

# Should open a browser window - if not go to http//127.0.0.1:5001
```

### On each of your spare machines - with blender already installed
```
$ pip install git+https://github.com/tf198/houseblend.git

$ houseblend-worker <manager-ip>
# or if blender is in a weird place
$ houseblend-worker <manager-ip>
```

## To start a render
* Click the 

## Design
