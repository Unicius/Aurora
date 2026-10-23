class SlicerAPI:
    """Взаимодействие с API STE Slicer (Cura Framework)"""
    
    @staticmethod
    def set_setting_value(key: str, value: str):
        """Установка параметра печати (температура, скорость, заполнение)"""
        # В реальном слайсере: Application.getInstance().getGlobalContainerStack().setProperty(key, "value", value)
        print(f"[STE Slicer API] Set setting '{key}' = {value}")
        return True

    @staticmethod
    def set_print_mode(mode: str):
        """Переключение между 3D и 5D режимом"""
        print(f"[STE Slicer API] Print mode changed to: {mode}")
        return True
