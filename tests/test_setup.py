class Shape:
    pass


class Circle(Shape):
    def area(self):
        return sum(self.radius)


def main():
    c = Circle()
    print(c.area())
