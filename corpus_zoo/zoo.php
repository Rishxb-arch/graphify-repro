<?php
class Dog {
    function speak() { return $this->bark(); }
    function bark() { return "woof"; }
}
class Cat {
    function speak() { return "meow"; }
    function bark() { return "hiss"; }
}
