# HouseBlend

Simple Blender rendering using your home network

## Instructions

### On your workstation
```
pip install houseblend

# change into whatever directory contains your working blendfiles
cd projects

# run the manager
houseblend manager
```

### On each of your spare machines
```
pip instal houseblend
houseblend worker <ip of manager>
```