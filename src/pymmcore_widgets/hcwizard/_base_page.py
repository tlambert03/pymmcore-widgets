from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QWizardPage

from ._wizard_model import WizardModel


class ConfigWizardPage(QWizardPage):
    def __init__(self, model: WizardModel, core: CMMCorePlus):
        super().__init__()
        self._model = model
        self._core = core
