import ipyvolume as ipv
import ipywidgets as widgets
import traitlets
import numpy as np
from IPython.display import display

from glue_vispy_viewers.common.viewer_state import Vispy3DViewerState
from glue_vispy_viewers.scatter.viewer_state import Vispy3DScatterViewerState
from glue.core.roi import PolygonalROI, CircularROI, RectangularROI, Projected3dROI
from glue.core.subset import RoiSubsetState3d
from glue.core.command import ApplySubsetState
from glue.viewers.common.qt.data_viewer_with_state import DataViewerWithState

from .. import IPyWidgetView
from ..link import link, link_component_id_to_select_widget
from .scatter import IpyvolumeScatterLayerArtist
from .volume import IpyvolumeVolumeLayerArtist


class IpyvolumeVolumeViewerState(Vispy3DViewerState):
    def __init__(self, **kwargs):
        super(IpyvolumeVolumeViewerState, self).__init__()
        self.add_callback('layers', self._update_attributes)
        self.update_from_dict(kwargs)

    def _update_attributes(self, *args):
        for layer_state in self.layers:
            if getattr(layer_state.layer, 'ndim', None) == 3:
                data = layer_state.layer
                break
        else:
            data = None

        if data is None:
            type(self).x_att.set_choices(self, [])
            type(self).y_att.set_choices(self, [])
            type(self).z_att.set_choices(self, [])

        else:
            z_cid, y_cid, x_cid = data.pixel_component_ids

            type(self).x_att.set_choices(self, [x_cid])
            type(self).y_att.set_choices(self, [y_cid])
            type(self).z_att.set_choices(self, [z_cid])


class IpyvolumeScatterViewerState(Vispy3DScatterViewerState):
    pass


#from .scatter import Scatter3dViewerState as IpyvolumeVolumeViewerState

class IpyvolumeBaseView(IPyWidgetView):
    allow_duplicate_data = False
    allow_duplicate_subset = False

    # _layer_style_widget_cls = {VolumeLayerArtist: IpyvolumeLayerStyleWidget,
    #                            ScatterLayerArtist: IpyvolumeScatterLayerArtist}

    def __init__(self, *args, **kwargs):
        super(IpyvolumeBaseView, self).__init__(*args, **kwargs)

        self.state = self._state_cls()
        self.figure = ipv.figure(animation_exponent=1.)
        self.figure.on_selection(self.on_selection)

        self.create_tab()

        self.state.add_callback('x_min', self.limits_to_scales)
        self.state.add_callback('x_max', self.limits_to_scales)
        self.state.add_callback('y_min', self.limits_to_scales)
        self.state.add_callback('y_max', self.limits_to_scales)
        self.output_widget = widgets.Output()
        self.main_widget = widgets.VBox(
            children=[self.tab, ipv.gcc(), self.output_widget])

    def show(self):
        display(self.main_widget)

    def on_selection(self, data, other=None):
        with self.output_widget:
            W = np.matrix(self.figure.matrix_world).reshape((4, 4))     .T
            P = np.matrix(self.figure.matrix_projection).reshape((4, 4)).T
            M = np.dot(P, W)
            if data['device']:
                if data['type'] == 'lasso':
                    region = data['device']
                    vx, vy = zip(*region)
                    roi_2d = PolygonalROI(vx=vx, vy=vy)
                elif data['type'] == 'circle':
                    x1, y1 = data['device']['begin']
                    x2, y2 = data['device']['end']
                    dx = x2 - x1
                    dy = y2 - y1
                    r = (dx**2 + dy**2)**0.5
                    roi_2d = CircularROI(xc=x1, yc=y1, radius=r)
                elif data['type'] == 'rectangle':
                    x1, y1 = data['device']['begin']
                    x2, y2 = data['device']['end']
                    x = [x1, x2]
                    y = [y1, y2]
                    roi_2d = RectangularROI(
                        xmin=min(x), xmax=max(x), ymin=min(y), ymax=max(y))
                roi = Projected3dROI(roi_2d, M)
                self.apply_roi(roi)

    def apply_roi(self, roi):
        if len(self.layers) > 0:
            # self.state.x_att.parent.get_component(self.state.x_att)
            x = self.state.x_att
            # self.state.y_att.parent.get_component(self.state.y_att)
            y = self.state.y_att
            # self.state.z_att.parent.get_component(self.state.z_att)
            z = self.state.z_att
            subset_state = RoiSubsetState3d(x, y, z, roi)
            cmd = ApplySubsetState(data_collection=self._data,
                                   subset_state=subset_state)
            self._session.command_stack.do(cmd)

    def limits_to_scales(self, *args):
        if self.state.x_min is not None and self.state.x_max is not None:
            self.figure.xlim = self.state.x_min, self.state.x_max
        if self.state.y_min is not None and self.state.y_max is not None:
            self.figure.ylim = self.state.y_min, self.state.y_max
        # if self.state.z_min is not None and self.state.z_max is not None:
        #     self.figure.zlim = self.state.z_min, self.state.z_max
        if self.state.y_min is not None and self.state.y_max is not None:
            self.figure.zlim = self.state.y_min, self.state.y_max

    def redraw(self):
        pass

    def create_tab(self):
        self.widget_show_axes = widgets.Checkbox(value=False, description="Show axes")
        link((self.state, 'visible_axes'), (self.widget_show_axes, 'value'))
        def change(change):
            with self.figure:
                if change.new:
                    ipv.style.axes_on()
                    ipv.style.box_on()
                else:
                    ipv.style.axes_off()
                    ipv.style.box_off()
        self.widget_show_axes.observe(change, 'value')


        self.widgets_axis = []
        for i, axis_name in enumerate('xyz'):
            helper = getattr(self.state, axis_name + '_att_helper')
            widget_axis = widgets.Dropdown(options=[k.label for k in helper.choices],
                                           value=getattr(self.state, axis_name + '_att'), description=axis_name + ' axis')
            self.widgets_axis.append(widget_axis)
            link_component_id_to_select_widget(self.state, axis_name + '_att', widget_axis)

        selectors = ['lasso', 'circle', 'rectangle']
        self.button_action = widgets.ToggleButtons(description='Mode: ', options=[(selector, selector) for selector in selectors],
                                                   icons=["arrows", "pencil-square-o"])
        traitlets.link((self.figure, 'selector'),
                       (self.button_action, 'label'))

        self.tab_general = widgets.VBox([self.button_action, self.widget_show_axes] + self.widgets_axis)#, self.widget_y_axis, self.widget_z_axis])
        children = [self.tab_general]
        self.tab = widgets.Tab(children)
        self.tab.set_title(0, "General")
        self.tab.set_title(1, "Axes")

IpyvolumeBaseView.add_data = DataViewerWithState.add_data
IpyvolumeBaseView.add_subset = DataViewerWithState.add_subset

class IpyvolumeScatterView(IpyvolumeBaseView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    _state_cls = IpyvolumeScatterViewerState
    _data_artist_cls = IpyvolumeScatterLayerArtist
    _subset_artist_cls = IpyvolumeScatterLayerArtist

    def get_data_layer_artist(self, layer=None, layer_state=None):
        layer = self.get_layer_artist(self._data_artist_cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer

    def get_subset_layer_artist(self, layer=None, layer_state=None):
        layer = self.get_layer_artist(self._subset_artist_cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer


class IpyvolumeVolumeView(IpyvolumeBaseView):
    _state_cls = IpyvolumeVolumeViewerState


    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = IpyvolumeScatterLayerArtist
        else:
            cls = IpyvolumeVolumeLayerArtist
        #print('layer', layer, cls)
        layer = self.get_layer_artist(cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer

    def get_subset_layer_artist(self, layer=None, layer_state=None):
        return self.get_data_layer_artist(layer, layer_state)

    def create_tab(self):
        children = []
        self.tab = widgets.Tab(children)

