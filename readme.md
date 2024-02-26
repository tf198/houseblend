# HouseBlend

Simple Blender rendering using your home network.

## Instructions

### On your workstation
```
$ pip install houseblend

# change into whatever directory contains your working blendfiles
$ cd projects

# run the manager
$ houseblend manager

# Should open a browser window - if not go to http//127.0.0.1:5001
```

### On each of your spare machines
```
$ pip instal houseblend
$ houseblend worker <ip of manager>
```

## Design
