Vagrant.configure("2") do |config|
  config.vm.box = "peru/ubuntu-18.04-desktop-amd64"


  config.vm.synced_folder ".", "/vagrant", type: "rsync", disabled: true

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "4096"
    vb.cpus = "1"
    vb.customize ["modifyvm", :id, "--vram", "128"]
  end

  config.vm.provision "shell", privileged: false, inline: <<-SHELL

echo "whoami..."
whoami

echo "pwd..."
pwd

# commented out to speed things up, do not do this in production
# echo "updating..."
# sudo yum update -y

sudo apt-get update
sudo apt-get install -y alsa pulseaudio
sudo apt install git -y
sudo git clone https://github.com/MycroftAI/mycroft-core.git
cd mycroft-core
printf "y/y/y/y/y" | sudo ./dev_setup.sh -fm --allow-root; printf "\n\y" | sudo ./dev_setup.sh --allow-root
sudo reboot

  SHELL

end
