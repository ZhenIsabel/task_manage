# coding:utf-8
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout

from qfluentwidgets import InfoBarIcon, InfoBar, PushButton, FluentIcon, InfoBarPosition, InfoBarManager


@InfoBarManager.register('Custom')
class CustomInfoBarManager(InfoBarManager):
    """ Custom info bar manager """

    def _pos(self, infoBar: InfoBar, parentSize=None):
        p = infoBar.parent()
        parentSize = parentSize or p.size()

        # the position of first info bar
        x = (parentSize.width() - infoBar.width()) // 2
        y = (parentSize.height() - infoBar.height()) // 2

        # get the position of current info bar
        index = self.infoBars[p].index(infoBar)
        for bar in self.infoBars[p][0:index]:
            y += (bar.height() + self.spacing)

        return QPoint(x, y)

    def _slideStartPos(self, infoBar: InfoBar):
        pos = self._pos(infoBar)
        return QPoint(pos.x(), pos.y() - 16)

def createInfoInfoBar(parent:QWidget,content):
        w = InfoBar(
            icon=InfoBarIcon.INFORMATION,
            title='Title',
            content=content,
            orient=Qt.Vertical,    # vertical layout
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=parent
        )
        w.addWidget(PushButton('Action'))
        w.show()

def createSuccessInfoBar(parent:QWidget,title,content):
        # convenient class mothod
        InfoBar.success(
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            # position='Custom',   # NOTE: use custom info bar manager
            duration=2000,
            parent=parent
        )