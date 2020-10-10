# MicroPython SOCKS server

A MicroPython library for SOCKS server.

## Installation

Installation can be done using upip or by manually uploading it to the device.

## Easy Installation

Just install it using upip - standard micropython packaging.
```
import upip
upip.install('micropython-socks')
```

## Manual Installation

Copy the file to your device, using ampy, webrepl or compiling and deploying. eg.

```
$ ampy put socks.py
```

# Usage

```python
import socks
socks.start()
```

```python
import socks
socks.stop()
```

```python
import socks
socks.help()
```

# Development

Building for distribution:
```
python setup.py sdist
```

Distribution of release:
```
python setup.py sdist
pip install twine
twine upload dist/*
```

## Links

* [micropython.org](http://micropython.org)
* [Adafruit Ampy](https://learn.adafruit.com/micropython-basics-load-files-and-run-code/install-ampy)
* [ESP32 PPP by Emard](https://github.com/emard/esp32ppp)

# License

Licensed under the [MIT License](http://opensource.org/licenses/MIT).
