````mermaid
classDiagram

    class CarnivorousPlant {
    }
    class Omnivore {
    }
    class PlantParts {
    }
    class animal {
    }
    class carnivore {
    }
    class herbivore {
    }
    class lion {
    }
    class plant {
    }
    class Thing {
    }

    %% SubClassOf
    plant  <|-- CarnivorousPlant
    animal <|-- Omnivore
    animal <|-- carnivore
    animal <|-- herbivore
    animal <|-- lion
    Thing  <|-- PlantParts

    %% eats
    lion           --> herbivore  : eats
    carnivore      --> animal     : eats
    herbivore      --> plant      : eats
    herbivore      --> PlantParts : eats
    Omnivore       --> animal     : eats
    Omnivore       --> plant      : eats
    Omnivore       --> PlantParts : eats
    CarnivorousPlant --> animal   : eats

    %% is-proper-part-of
    PlantParts --> plant : is-proper-part-of

    %% is-part-of / has-part
    PlantParts --> plant : is-part-of
    plant      --> PlantParts : has-part
`

```

```
````
