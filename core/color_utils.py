"""
颜色工具类，用于处理颜色范围随机选择
"""
import random
import colorsys
from PyQt6.QtGui import QColor
import logging

logger = logging.getLogger(__name__)

class ColorUtils:
    """颜色工具类"""
    
    @staticmethod
    def hex_to_hsv(hex_color):
        """将十六进制颜色转换为HSV"""
        color = QColor(hex_color)
        return color.hue(), color.saturation(), color.value()
    
    @staticmethod
    def hsv_to_hex(h, s, v):
        """将HSV转换为十六进制颜色"""
        color = QColor()
        color.setHsv(int(h), int(s), int(v))
        return color.name()
    
    @staticmethod
    def get_random_color_in_range(base_color, hue_range=30, saturation_range=20, value_range=20):
        """
        在指定颜色范围内生成随机颜色
        
        Args:
            base_color: 基础颜色（十六进制格式，如 "#FF6B6B"）
            hue_range: 色相变化范围（0-360）
            saturation_range: 饱和度变化范围（0-255）
            value_range: 明度变化范围（0-255）
        
        Returns:
            随机颜色的十六进制字符串
        """
        try:
            # 转换为HSV
            h, s, v = ColorUtils.hex_to_hsv(base_color)
            
            # 处理色相的特殊情况（-1表示无色相，如灰色）
            if h == -1:
                h = 0
            
            # 生成随机偏移
            h_offset = random.randint(-hue_range//2, hue_range//2)
            s_offset = random.randint(-saturation_range//2, saturation_range//2)
            v_offset = random.randint(-value_range//2, value_range//2)
            
            # 计算新颜色
            new_h = (h + h_offset) % 360
            new_s = max(0, min(255, s + s_offset))
            new_v = max(0, min(255, v + v_offset))
            
            # 转换回十六进制
            return ColorUtils.hsv_to_hex(new_h, new_s, new_v)
            
        except Exception as e:
            logger.error(f"生成随机颜色失败: {str(e)}")
            return base_color  # 如果出错，返回原颜色
    
    @staticmethod
    def get_quadrant_random_color(quadrant_id, config):
        """
        根据象限ID和配置获取随机颜色
        
        Args:
            quadrant_id: 象限ID（'q1', 'q2', 'q3', 'q4'）
            config: 配置对象
        
        Returns:
            随机颜色的十六进制字符串
        """
        try:
            # 获取象限的基础颜色
            base_color = config['quadrants'][quadrant_id]['color']
            
            # 获取颜色范围设置
            color_ranges = config.get('color_ranges', {})
            quadrant_range = color_ranges.get(quadrant_id, {})
            
            # 获取范围参数，如果没有设置则使用默认值
            hue_range = quadrant_range.get('hue_range', 30)
            saturation_range = quadrant_range.get('saturation_range', 20)
            value_range = quadrant_range.get('value_range', 20)
            
            # 生成随机颜色
            return ColorUtils.get_random_color_in_range(
                base_color, hue_range, saturation_range, value_range
            )
            
        except Exception as e:
            logger.error(f"获取象限随机颜色失败 (quadrant: {quadrant_id}): {str(e)}")
            # 如果出错，返回基础颜色
            return config['quadrants'][quadrant_id]['color']
