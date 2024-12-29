from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton


class SynthInterfaceApp(App):
    def build(self):
        # Main Layout
        main_layout = GridLayout(cols=3, padding=10, spacing=10)

        # ADSR Section
        main_layout.add_widget(Label(text="ADSR", bold=True, size_hint=(1, 0.1)))
        for label in ["Attack", "Decay", "Sustain", "Release"]:
            knob_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
            knob_layout.add_widget(Label(text=label, size_hint=(1, 0.2)))
            slider = Slider(min=0, max=100, value=50, size_hint=(1, 0.8))
            slider.bind(value=self.on_slider_change)
            knob_layout.add_widget(slider)
            main_layout.add_widget(knob_layout)

        # Oscillator Section
        main_layout.add_widget(Label(text="Oscillators", bold=True, size_hint=(1, 0.1)))
        for osc in ["Sin", "Saw", "Tri", "Pulse"]:
            knob_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
            knob_layout.add_widget(Label(text=osc, size_hint=(1, 0.2)))
            slider = Slider(min=-60, max=60, value=0, size_hint=(1, 0.8))
            slider.bind(value=self.on_slider_change)
            knob_layout.add_widget(slider)
            main_layout.add_widget(knob_layout)

        # Filter Section
        main_layout.add_widget(Label(text="Filter", bold=True, size_hint=(1, 0.1)))
        knob_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        knob_layout.add_widget(Label(text="P Cutoff", size_hint=(1, 0.2)))
        cutoff_slider = Slider(min=0, max=100, value=50, size_hint=(1, 0.8))
        cutoff_slider.bind(value=self.on_slider_change)
        knob_layout.add_widget(cutoff_slider)
        main_layout.add_widget(knob_layout)

        knob_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        knob_layout.add_widget(Label(text="Reson", size_hint=(1, 0.2)))
        reson_slider = Slider(min=0, max=100, value=8, size_hint=(1, 0.8))
        reson_slider.bind(value=self.on_slider_change)
        knob_layout.add_widget(reson_slider)
        main_layout.add_widget(knob_layout)

        # Filter Switches
        switch_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        switch_layout.add_widget(Label(text="Filter Type", size_hint=(1, 0.2)))
        for mode in ["HP", "LP", "Bypass"]:
            toggle = ToggleButton(text=mode, size_hint=(1, 0.2), group="filter")
            switch_layout.add_widget(toggle)
        main_layout.add_widget(switch_layout)

        # Noise Section
        main_layout.add_widget(Label(text="Noise", bold=True, size_hint=(1, 0.1)))
        noise_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        noise_layout.add_widget(Label(text="Noise Level", size_hint=(1, 0.2)))
        noise_slider = Slider(min=0, max=100, value=0, size_hint=(1, 0.8))
        noise_slider.bind(value=self.on_slider_change)
        noise_layout.add_widget(noise_slider)
        main_layout.add_widget(noise_layout)

        # FX Section
        main_layout.add_widget(Label(text="FX", bold=True, size_hint=(1, 0.1)))
        fx_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        for fx in ["Clipper", "Bypass"]:
            toggle = ToggleButton(text=fx, size_hint=(1, 0.2), group="fx")
            fx_layout.add_widget(toggle)
        main_layout.add_widget(fx_layout)

        return main_layout

    def on_slider_change(self, instance, value):
        print(f"{instance} changed to {value}")


# Run the app
if __name__ == "__main__":
    SynthInterfaceApp().run()
