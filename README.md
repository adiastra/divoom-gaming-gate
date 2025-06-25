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
![image](https://github.com/user-attachments/assets/dbe939a9-b183-4318-af6e-76c9cc03dbd2)



In this screen, you can load any image or animated GIF from either your local machine or Tenor GIF Search. You can skip frames (for sending large GIFs faster) and edit the time between frames. This screen also allows you to change the aspect of the image to Stretch, Fit, or Crop the image for the best fit. You can also save sets of images as themes. 


-------------

![image](https://github.com/user-attachments/assets/c5f4c5e1-7413-49fe-9a7b-7f370e7f33d6)


This screen allows you to send "Themes" to the screens. Themes are collections of 5 mages that are all sent to the screen atthe same time. These allow you to create ambiance for different "scenes" in your adventure. 

-------------

![image](https://github.com/user-attachments/assets/2b6431e4-c73a-4984-bbc7-3cce2fa2080e)


This screen allows you to create character images with backgrounds and character stats. You can use the default system layouts (D&D / Genesys) or roll your own, which you can then save for future use. It allows every stat to be either a single number, an X/Y ,configuration and allows you to add modifiers (like +1 or -2) 

-------------

![image](https://github.com/user-attachments/assets/bfbe22e6-f240-4a24-9748-b2f1f12ee8c9)


This area is mostly self-explanatory and utilizes some of the built-in tools that are part of the Divoom API. There is a stopwatch, a timer, a countdown timer, a scoreboard (red vs blue), a noise meter and an image splitter (for splitting any image into 5 images that can be sent to the screens).  

-------------

![image](https://github.com/user-attachments/assets/4c0a478a-19e3-497b-941f-93737c84ff3b)


a built-in designer that allows you to design new gifs (including animations) and send them to the screens. 

-------------

![image](https://github.com/user-attachments/assets/dff08b21-fd17-43b0-9ed6-e7686362ff29)



Settings for the clock, brightness, and IP address (An IP is required for the app to work) and a place to check for updates. 

