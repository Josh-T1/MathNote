

# Controlling the Keyboard
[controler]
* Press and release keys
```python
with keyboard.pressed(Key.shift):
    keyboard.press('a')
    keyboard.release('a')
```


# Monitoring the Keyboard
1. Blocking
```
with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()
```
2. Non Blockig
```
listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()
```

1. keyboard listener is a threading.Thread
1. Key parameter passed to callbacks are
    2. Keyboard.Key for special keys
    2. keyboard.KeyCode for normal alphanumeric keys
    2. None for unknown keys

# Global Hotkeys
```
def on_activate():
    print('Global hotkey activated!')

def for_canonical(f):
    return lambda k: f(l.canonical(k))

hotkey = keyboard.HotKey(
    keyboard.HotKey.parse('<ctrl>+<alt>+h'),
    on_activate)
with keyboard.Listener(
        on_press=for_canonical(hotkey.press),
        on_release=for_canonical(hotkey.release)) as l:
    l.join()
```
1. for_canonical takes on_press function. Listener conical function is called
   and key is passed. Method to remove modifier state from the events
