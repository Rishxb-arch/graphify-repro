class Dog {
  speak(): string { return this.bark(); }
  bark(): string { return "woof"; }
}
class Cat {
  speak(): string { return "meow"; }
  bark(): string { return "hiss"; }
}
