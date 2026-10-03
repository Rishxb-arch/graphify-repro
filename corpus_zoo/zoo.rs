struct Dog;
struct Cat;
impl Dog {
    fn speak(&self) -> &str { self.bark() }
    fn bark(&self) -> &str { "woof" }
}
impl Cat {
    fn speak(&self) -> &str { "meow" }
    fn bark(&self) -> &str { "hiss" }
}
