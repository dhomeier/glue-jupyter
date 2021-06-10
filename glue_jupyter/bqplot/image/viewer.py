from glue.viewers.image.state import ImageViewerState
from glue.viewers.image.composite_array import CompositeArray
from bqplot_image_gl.viewlistener import ViewListener

from ...link import on_change

from ..common.viewer import BqplotBaseView
from ..scatter.layer_artist import BqplotScatterLayerArtist

from .layer_artist import BqplotImageLayerArtist, BqplotImageSubsetLayerArtist
from .frb_mark import FRBImage

from glue_jupyter.common.state_widgets.layer_scatter import ScatterLayerStateWidget
from glue_jupyter.common.state_widgets.layer_image import (ImageLayerStateWidget,
                                                           ImageSubsetLayerStateWidget)
from glue_jupyter.common.state_widgets.viewer_image import ImageViewerStateWidget

__all__ = ['BqplotImageView']


class BqplotImageView(BqplotBaseView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    large_data_size = 2e7

    _layer_style_widget_cls = {BqplotImageLayerArtist: ImageLayerStateWidget,
                               BqplotImageSubsetLayerArtist: ImageSubsetLayerStateWidget,
                               BqplotScatterLayerArtist: ScatterLayerStateWidget}
    _state_cls = ImageViewerState
    _options_cls = ImageViewerStateWidget

    tools = ['bqplot:home', 'bqplot:panzoom', 'bqplot:rectangle', 'bqplot:circle']

    def __init__(self, session):

        super(BqplotImageView, self).__init__(session)

        self._composite = CompositeArray()
        self._composite_image = FRBImage(self, self._composite)
        self.figure.marks = list(self.figure.marks) + [self._composite_image]
        self.state.add_callback('reference_data', self._reset_limits)
        self.state.add_callback('x_att', self._reset_limits)
        self.state.add_callback('y_att', self._reset_limits)

        self._setup_view_listener()

        on_change([(self.state, 'aspect')])(self._sync_figure_aspect)
        self._sync_figure_aspect()

    def _setup_view_listener(self):
        self._vl = ViewListener(widget=self.figure,
                                css_selector=".plotarea_events")
        self._vl.observe(self._on_view_change, names=['view_data'])

    def _reset_limits(self, *args):
        self.state.reset_limits()

    def _on_view_change(self, *args):
        views = sorted(self._vl.view_data)
        if len(views) > 0:
            first_view = self._vl.view_data[views[0]]
            self._composite_image.shape = (int(first_view['height']), int(first_view['width']))
        else:
            self._composite_image.shape = None
        self._sync_figure_aspect()

    def _sync_figure_aspect(self, *args, **kwargs):
        with self.figure.hold_trait_notifications():
            if self.state.aspect == 'equal':
                if self._composite_image.shape is None:
                    axes_ratio = None
                else:
                    height, width = self._composite_image.shape
                    axes_ratio = height / width
            else:
                axes_ratio = None
            self.state._set_axes_aspect_ratio(axes_ratio)

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = BqplotScatterLayerArtist
        else:
            cls = BqplotImageLayerArtist
        return self.get_layer_artist(cls, layer=layer, layer_state=layer_state)

    def get_subset_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = BqplotScatterLayerArtist
        else:
            cls = BqplotImageSubsetLayerArtist
        return self.get_layer_artist(cls, layer=layer, layer_state=layer_state)
