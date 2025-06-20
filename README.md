# Divoom Gaming Gate

## What is it?

This is a work in progress designed to allow users to push images to the [ Divoom Times Gate](https://divoom.com/products/time-gate)

It is written in Python and utilizes the PyQt5, Pillow, and requests libraries. 


## How to install and run

You can install the application using pip/pipx/pip3 or any other Python manager that communicates with PyPI. It will take some time to launch on first launch (pycache is being generated), but after that it will launch normally. 

```
pip install divoom-gaming-gate
```
or
```
pipx install divoom-gaming-gate
```
or
```
pip3 install divoom-gaming-gate
```

You may have to ask it to install dependencies like this 

```
pipx install divoom-gaming-gate --include-deps
```

Then just run it from the command line
```
divoom-gaming-gate
```
## Screenshots and description
![image](https://github.com/user-attachments/assets/4a188fc9-d230-45f7-ae97-af73320d0153)


In this screen, you can load any image or animated GIF from either your local machine or Tenor GIF Search. You can skip frames (for sending large GIFs faster) and edit the time between frames. This screen also allows you to change the aspect of the image to Stretch, Fit, or Crop the image for best fit. 


-------------

![image](https://github.com/user-attachments/assets/a2f51d4b-0b9f-4eb4-a898-7b9c2e3849c1)


This screen allows you to create character images with backgrounds and character stats. You can use the default system layouts (D&D / Genesys) or roll your own, which you can then save for future use. It allows every stat to be either a single number, an X/Y ,configuration and allows you to add modifiers (like +1 or -2) 

-------------

![image](https://github.com/user-attachments/assets/4e96599e-1f42-43b7-876a-9482a0d88f88)


This area is mostly self-explanatory and utilizes some of the built-in tools that are part of the Divoom API

-------------

![image](https://github.com/user-attachments/assets/1cb2a74c-7c98-46db-ac8a-2287d32c0c34)


a built in designer that allows you to design new gifs (including animations) and send them to the screens. 

-------------

![image](https://github.com/user-attachments/assets/5ab4c357-bb88-4a20-8fe7-27e08df58e63)


Settings for the clock, brightness, and IP address (An IP is required for the app to work) 

