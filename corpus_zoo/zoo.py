class Dog:
    def speak(self):
        return self.bark()      # must bind to Dog.bark

    def bark(self):
        return "woof"


class Cat:
    def speak(self):
        return "meow"

    def bark(self):
        return "hiss"
