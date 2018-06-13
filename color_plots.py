import tkinter as tk
from collections import deque

from matplotlib import pyplot as plt
import matplotlib.animation as animation
import matplotlib.backends.tkagg as tkagg
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg


class FILOQueue:
    def __init__(self, length):
        self._list = deque([0] * length)

    def __len__(self) -> int:
        return len(self._list)

    def put(self, value):
        self._list.rotate(1)
        self._list[0] = value

    def __repr__(self):
        return str(self._list)

    def __getitem__(self, key):
        return self._list[key]

    def __iter__(self):
        for e in self._list:
            yield e

    def __contains__(self, item):
        return item in self._list


class ColorPlot(tk.Canvas):
    """https://matplotlib.org/gallery/user_interfaces/embedding_in_tk_canvas_sgskip.html"""

    def __init__(self, master, color_hsbk):
        super().__init__(master=master, width=300, height=400)
        self.parameters_dict = {0: "hue",
                                1: "saturation",
                                2: "brightness",
                                3: "kelvin"}
        self.hsbk = color_hsbk

        # Create containers for values
        self.figs = {}
        self.subplots = {}
        self.plots = {}
        self.lines = {}
        self.fig_photos = {}
        self.animations = {}

        # Create the axes
        self.plot_length = 100
        self.HSBKx = np.linspace(0, self.plot_length, self.plot_length)
        self.values = {}
        for idx, parameter in self.parameters_dict.items():
            self.values[parameter] = FILOQueue(self.plot_length)
            self.values[parameter].put(self.hsbk[idx].get())

            # Create the figure we desire to add to an existing canvas
            self.figs[parameter] = plt.figure(figsize=(2, 1))
            self.subplots[parameter] = self.figs[parameter].add_subplot(1, 1, 1)
            self.lines[parameter], = self.subplots[parameter].plot(self.HSBKx, self.values[parameter])

            # Keep this handle alive, or else figure will disappear
            fig_x, fig_y = self.plot_length, self.plot_length
            self.fig_photos[parameter] = self.draw_figure(self.figs[parameter], loc=(fig_x, fig_y * idx + 5))

            self.animations[parameter] = animation.FuncAnimation(self.figs[parameter],
                                                                 lambda *_, var=idx, self=self: self.update_plot(var),
                                                                 blit=False)

        # Trace variable changes
        # for idx, parameter in self.parameters_dict.items():
        #   self.hsbk[idx].trace('w', lambda *_, var=idx, self=self: self.update_plot(var))

    def draw_figure(self, figure, loc=(0, 0)):
        figure_canvas_agg = FigureCanvasAgg(figure)
        figure_canvas_agg.draw()
        figure_x, figure_y, figure_w, figure_h = figure.bbox.bounds
        figure_w, figure_h = int(figure_w), int(figure_h)
        photo = tk.PhotoImage(master=self, width=figure_w, height=figure_h)

        # Position: convert from top-left anchor to center anchor
        self.create_image(loc[0] + figure_w / 2, loc[1] + figure_h / 2, image=photo)

        # Unfortunately, there's no accessor for the pointer to the native renderer
        tkagg.blit(photo, figure_canvas_agg.get_renderer()._renderer, colormode=2)

        # Return a handle which contains a reference to the photo object
        # which must be kept live or else the picture disappears
        return photo

    def update_plot(self, param_id: int):
        print('updatin')
        parameter: str = self.parameters_dict[param_id]
        self.values[parameter].put(self.hsbk[param_id].get())
        self.lines[parameter].set_data(self.HSBKx, self.values[parameter])
