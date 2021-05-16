from manim import *

class CircleTest(Scene):
    def construct(self):
        a = Circle()
        self.play(Create(a))