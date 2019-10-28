# OpenSight: the powerful, easy-to-use vision suite

<p align="center">
    <a href="https://discordapp.com/invite/hPqpdsK">
        <img src="https://img.shields.io/discord/573690061720125441?label=Discord&style=flat"
            alt="Join our Server"></a>
    <a href="https://github.com/opensight-cv/opensight/blob/master/LICENSE">
        <img src="https://img.shields.io/github/license/opensight-cv/opensight?style=flat"
            alt="MIT License"></a>
    <a href="https://github.com/opensight-cv/opsi-gen/releases/latest">
        <img src="https://img.shields.io/github/v/release/opensight-cv/opsi-gen?style=flat"
            alt="Latest Release Image"></a>
    <a href="https://github.com/opensight-cv/opensight/commits/master">
        <img src="https://img.shields.io/github/last-commit/opensight-cv/opensight?style=flat"
            alt="Last Commit"></a>
    <a href="https://github.com/opensight-cv/opensight/stargazers">
        <img src="https://img.shields.io/github/stars/opensight-cv/opensight?style=flat"
            alt="Stars"></a>
</p>

OpenSight is an FRC-focused, free and open source computer vision system targeted specifically for the Raspberry Pi. Our goal is to make it easy for people not familiar with vision to be able to make complex pipelines, while also providing powerful functionality for advanced users.

## Want to get it?
For Raspberry Pi, Download the [latest release image](https://github.com/opensight-cv/opsi-gen/releases/latest), flash it onto a micro-sd card, plug it in, then navigate to http://opensight.local once connected to a robot network.

For installing OpenSight on non-Raspberry Pi devices and for upgrading from previous versions of OpenSight, you can find more information [here](https://github.com/opensight-cv/packages#how-do-i-upgrade-an-existing-installation-of-opensight).

![OpenSight Nodetree](images/simple_nodetree.png "OpenSight Nodetree")

## About

Our mission is to create an accessible vision suite, with an easy-to-use and works out-of-the box experience, but also allow for more power and greater customizability. We want to make vision more accessible to those with less experience, while also providing the tools for power users and developers to easily add features beyond the default modules.

### Have any questions, comments, or want to contribute?
Join the OpenSight [Discord server](https://discord.gg/hPqpdsK)!

## How it works
The main components of the OpenSight vision framework are the **modules** and the **pipeline**. 
Vision modules can be connected to each other to form a vision pipeline used to detect and track vision targets. The software that binds each module together in the backend is called the manager. OpenSight comes with basic modules such as input from a camera, OpenCV image processing functions, and a Camera Server implementation to show a camera stream on an FRC Dashboard.

### Modules
The modules determine what the vision pipeline tracks and to what extent. OpenSight modules take after cv image operations, allowing the user to have much greater control over the vision pipeline.

An example of a common pipeline: 
**Camera Input** -> **Blur** -> **HSV Range** -> **Find Contours** -> **Find Center** -> 
**NetworkTables**

This of course is just a simple setup, and because an OpenSight pipeline can split into multiple paths, you can customize as much as you want, and even track multiple targets at once.

One unique advantage of OpenSight is its extendability. You can create your own module and with a simple pull request, make it available to any other team! Currently the module documentation is a work in progress, but you can find great examples of how to setup basic modules in `opsi/modules/cv.py`.

# Licensing

OpenSight is free and open source software, now and forever. It is licensed under the MIT License. This means you can modify it, use the program commericially, and use it privately. You may also redistribute it, under the condition it is also distributed under the same or a stricter license. This statemenet is not legal advice, please read the license for full details. You can find the full terms of the license in the [LICENSE file](https://github.com/opensight-cv/opensight/tree/master/LICENSE).

**Font Awesome**

This project uses Font Awesome icons, as seen on the left navigation bar. Font Awesome is licensed under Creative Commons Attribution 4.0. You can find the details of this license [here](https://fontawesome.com/license/free).
