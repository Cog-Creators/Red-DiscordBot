.. source: https://gist.github.com/Twentysix26/cb4401c6e507782aa6698e9e470243ed

.. _host-list:

===================
Hosting Information
===================

.. note::
    This doc is written for the :ref:`hosting section <getting-started-hosting>`
    of the :ref:`getting started guide <getting-started>`. Please take a look
    if you don't know how to host Red.


| For your instance of Red to stay online 24/7, it needs to be hosted on a dedicated system.
  This page contains hosting related information and advice for beginners in 
  topics such as picking a provider.

First, we would like to make something clear:

.. warning::
    Due to their inability to handle Red's data structure and meet the
    conditions of being a supported platform; platforms such as Heroku, 
    Pterodactyl, repl.it, Termux and alike are **NOT** officially supported. 
    Docker support found in GitHub is also a work in progress and not ready
    for daily use. Workarounds for getting Red running on those platforms
    are imperfect due to Red's nature. You will not be able to receive
    support if an issue occurs when hosting on any of these platforms.


------------------------------------
Hosting on a VPS or Dedicated Server
------------------------------------

| You can host Red on a VPS running Linux or Windows. Using a Linux VPS is the
  recommended option. Dedicated servers also work but are overpowered and cost 
  ineffective unless one plans to run a very large bot or use their server for 
  more than just hosting Red. If you have already created an instance, Red can be moved to a different 
  server for hosting using the :doc:`backup/restore process </backup_red>`.

.. warning::
    Please be aware that a Linux server is controlled through a command line.
    If you don't know Unix basics, please take a look at
    `DigitalOcean's tutorial: An Introduction to Linux Basics
    <https://www.digitalocean.com/community/tutorials/an-introduction-to-linux-basics>`_.


------------
Self Hosting
------------

| It's possible to self host Red with your own hardware. A Raspberry Pi 3 
  will have enough computing capacity to handle a small to medium sized bot. 
  You can also host on your own computer or rack server. Any modern hardware 
  should work without issues. However, this option leaves you responsible for
  keeping the bot online by paying for electricity costs and dealing with power outages.

-------------------
Choosing a Provider
-------------------

| The following are some common providers suitable for hosting Red. With
  each having their pros and cons, this list is mainly intended to act as a
  starting point. You should conduct your own research and come to
  a conclusion depending on your needs and budget, taking into account
  providers not listed here if desired. The key is the provider offering 
  an OS supported by Red.

.. tip::
 You will have better results with Audio when the region in your Discord 
 server settings is closer to the bulk of the server's audience and
 the location you picked for your Red host.


-----------------
Average Providers
-----------------

| `Scaleway <https://www.scaleway.com/>`_ is a VPS and dedicated server
 provider French in origin with locations in Poland and Netherlands.

| `DigitalOcean <https://www.digitalocean.com/>`_ is a US based cloud services company 
 with locations available worldwide, the VPS service is provided under the brand name
 "Droplet".

| `OVH <https://us.ovhcloud.com/vps/>`_ is a company focused on providing hosting
 and cloud services with locations in Europe, North America and Asia Pacific.

| `Time4VPS <https://www.time4vps.com/>`_ is a Lithuanian VPS provider mainly focused
 on lower cost.

| `GalaxyGate <https://galaxygate.net/>`_ is a VPS and dedicated server provider
 with a single location in New York.

| `Linode <https://www.linode.com/>`_ is a US based cloud services company similar
 to DigitalOcean with locations available worldwide.

| `AWS Lightsail <https://aws.amazon.com/lightsail/>`_ is a VPS service from Amazon
 Web Services priced lower than their enterprise offerings.

| `Vultr <https://www.vultr.com/>`_ is a US based provider of VPS and dedicated servers
 with locations available worldwide.

| `Hetzner Online <https://www.hetzner.com/>`_ is a German VPS and dedicated server
 provider with locations in Germany, US and Finland.

| `Contabo <https://contabo.com/>`_ is also a German VPS and dedicated server provider
 with locations in Germany, Asia, Australia and the United States.

| `Ramnode <https://www.ramnode.com/>`_ is a US based VPS provider focused on
 low to middle end VPS with locations in the US and Netherlands.

| `LowEndBox <http://lowendbox.com/>`_ is a website where hosting providers are
 discussed and curated, often with lower costs and less known providers.

| `AlphaVps <https://alphavps.com>`_ is a Bulgarian VPS and dedicated server provider 
 with locations in Los Angeles, New York, England, Germany and Bulgaria.

--------------------
Higher End Providers
--------------------

| `AWS EC2 <https://aws.amazon.com/ec2/>`__ is the enterprise offering of Amazon Web Services.
 A limited free plan is available for 12 months, after which a complex pricing model with
 high costs take over.

| `Google Compute Engine <https://cloud.google.com/compute/>`__ is Google's EC2 competitor.
 However, an always free plan with limited resources is offered.

| `Microsoft Azure VM <https://azure.microsoft.com/services/virtual-machines/>`__ is
 Microsoft's EC2 competitor with lower costs than EC2 for Windows instances, but similar
 otherwise.

| `Oracle Cloud Compute  <https://www.oracle.com/cloud/compute/>`__ is Oracle's EC2
 competitor. But an always free plan is available with slightly higher specifications
 compared to that of Google Compute Engine.

------------
Free Hosting
------------

| `Google Compute Engine <https://cloud.google.com/free/docs/gcp-free-tier>`_,
  `Oracle Cloud Compute <https://oracle.com/cloud/free/#always-free>`_ and
  `AWS EC2 <https://aws.amazon.com/free/>`_ have free tier VPSes suitable for small bots.

| **Note:** The free tier offered by AWS for EC2 only lasts for 12 months, while
 Oracle Cloud and Google Cloud offer always free tiers with limited resources.

| Additionally, new Google Cloud customers get a $300 credit which is valid for 3 months.
 New Oracle Cloud customers also get $300 of free credit, but only valid for 30 days.

| Excluding the above, there is no recommended free VPS host. Persuasion of
 another individual for hosting Red is an option, albeit low in success rate.

.. warning::
    Please be aware that the Terms and Conditions of \"free\" providers often include
    the ability to terminate service at any time, for any reason, without warning or 
    consent from you. Make frequent data backups and always have a plan B host.

------------------
Securing Your Host
------------------

.. note::
    This section does not cover everything there is to know about system administration 
    and security, only a few basics with a plea to remain smart and diligent, securing
    your machine as much as possible from any and all threats.

| Installing Red and running your own bot is fun. Waking up to a crashed bot, server host compromise, 
etc. is not. Most VPSes are \"unmanaged\" and provide what is known as \"root access\". This means 
you are responsible for the server itself including maintenance, security patches, etc.

The first order of business is securing your server. At a baseline, you should be using SSH keys 
to login to your server on an account that is not root (disable root login). You can go further
by closing off SSH to the internet and only accessing through IP whitelist or secure VPN, but that 
is up to you and your security stance.

.. warning::
    Closing off the SSH port prior to giving yourself a way to access can and will lock you out of your server.
    Ensure that you have done due diligence or have a backup plan such as KVM access through your 
    hosting provider.

Next, you should configure `Automatic updates <https://documentation.ubuntu.com/server/how-to/software/automatic-updates/>`__ 
via the ``unattended-upgrades`` package. This ensures that you are automatically kept up to date with 
the latest security patches. Most stable LTS distributions work well with this package and cause no 
issues with system stability. Even though you are receiving automatic updates, you should try and plan monthly 
maintenance to restart the server to apply any kernel patches. Uptime in regards to time since last restart 
is not a bragging right, but a security blight.

For a more in-depth guide on how to secure your Linux host, see `DigitalOcean's tutorial: Recommended Security Measures to Protect Your Servers
    <https://www.digitalocean.com/community/tutorials/recommended-security-measures-to-protect-your-servers>`_.

------------------
Bot Best Practices
------------------

:ref:`Public bots are not supported. <end-user-guarantees>` Red was designed for server owners with a few servers. 
Knowing this, you should be aware of what servers your bot is in, including their member count and what cogs you 
make available to them. This allows you to choose the right amount of hardware to host your bot with.

For example, if you plan to make the ``audio`` cog available to the servers your bot is in, you should ramp up 
the amount of memory your host has to account for the increase in system requirements.

If your application is a part of a Team, you must understand that giving bot ownership permissions to the team 
is similar to giving all team members (Developer and above) access to your server host. 
The owner can access any data that is present on the host system.

.. warning::
    Only the person who is hosting Red should be owner. This has serious security implications.
    This also goes for passing owner and co-owner flags in the launch parameters.

Ultimately, as the owner, you are responsible for the security of your host and bot. You should know your way around
them and be able to troubleshoot, maintain, and fix them if you are planning to host Red (especially for others).