# wait for opensight to close before running script
while ps aux | grep opensight | grep [p]ython; do sleep 1; done
# force overwrite for stdeb
dpkg --force-overwrite -Ri "$1/deps"
apt-mark auto
for file in "$1/deps/"*; do
    name="$(dpkg -I $file | grep -m1 Package | cut -d ' ' -f3)"
    echo "Marking $name as auto"
    apt-mark auto "$name"
done
apt-mark manual "opensight"
dpkg -Ri "$1/system-deps"
apt-get -y autoremove
reboot
