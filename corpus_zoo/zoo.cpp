class Dog {
public:
    const char* speak() { return bark(); }
    const char* bark() { return "woof"; }
};
class Cat {
public:
    const char* speak() { return "meow"; }
    const char* bark() { return "hiss"; }
};
