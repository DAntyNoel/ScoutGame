# Scout！

An interesting poke board game for 2~5 players.

Rules are available at [How to Play Scout | Board Game Rules & Instructions (youtube.com)](https://www.youtube.com/watch?v=Ymb0YsMzP2M).

## Usage

Requirements:

```shell
pip install websockets
```

### Off-line Version

You can play `Scout!` against yourself on your own, using interactive shell command with

```shell
python offline.py
```

### On-line Version

Our project supports remote games. You can deploy this repository on a public server and start server with

```shell
python app.py
```

After that, you can connect remote server with [websockets](https://websockets.readthedocs.io/en/stable/intro/index.html). Here we provide a jupyter notebook connection [example (interact.ipynb)](./interact.ipynb) for you to interact with server, or the [GUI repository](). Remember to modify IP and ports where server is running and client connects.

TIPS: If you don't like the detailed INFO outputs, just set constant `DEBUG=False`.
