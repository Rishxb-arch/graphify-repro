package zoo

type Dog struct{}
type Cat struct{}

func (d Dog) Speak() string { return d.Bark() }
func (d Dog) Bark() string  { return "woof" }
func (c Cat) Speak() string { return "meow" }
func (c Cat) Bark() string  { return "hiss" }
