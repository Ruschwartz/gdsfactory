# Workflow

You'll need 2 windows:

1. A text editor or IDE (Visual Studio Code, Pycharm, Spyder, neovim, Atom, Jupyterlab ...)
2. Klayout to Visualize the GDS files. With the `klive` klayout package for showing GDS files when you run. Tools -> Manage Packages `Component.show()`

## 1. Standard Python flow

1. You write your PCells in python.
2. You execute the python code.
3. You visualize the GDS Layout in Klayout, or run simulations using the plugin extensions directly from the layout (for devices) or netlist (from circuits).

![windows](https://i.imgur.com/ZHEAotn.png)

## 2. File-watcher flow

For building large components you can use a file-watcher and see your updates in KLayout every time you save.

1. You execute the file watcher run this command on your terminal `gf watch --path /home/jmatres/my_chips` for watching `my_chips` folder or run it in the current working directory `gf watch --path .`
2. The file-watcher re-runs any python file `.py` or YAML `.pic.yml`. For testing it you can go to `gdsfactory/samples/demo/circuits`, modify any of the files and take a look how klayout updates every time you save a file.
3. Thanks to the `cell` cache you can see your new component changes live updating the layout in Klayout.

![filewatcher](https://i.imgur.com/DNWgVRp.png)

The file watcher works with python or `pic.yml`

![python](https://i.imgur.com/lscMlcJ.png)

or YAML

![yaml](https://i.imgur.com/PbJOhe1.png)

## 3. Schematic driven layout

1. You can use any Schematic capture tool. Lumerical interconnect, QUCS or Xschem. Save the netlist into SPICE format.
2. Convert SPICE to YAML. Since the schematic doesn't have placements you can infer the rough initial placements from the relative position of the schematic blocks.
3. Modify YAML with file watcher until you are happy with the placements.

![SDL](https://i.imgur.com/1VnCsPt.png)
