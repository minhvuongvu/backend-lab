package lab.{{PKG}}.web;

import java.util.UUID;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import lab.{{PKG}}.contract.ItemService;
import lab.{{PKG}}.domain.Item;

/**
 * Thin HTTP adapter over the contract; identical for every implementation so k6 drives the same API.
 */
@RestController
public class ItemController {

    private final ItemService items;

    public ItemController(ItemService items) {
        this.items = items;
    }

    public record CreateItem(@NotNull UUID id, @NotBlank String payload) {
    }

    @PostMapping("/items")
    public ResponseEntity<Item> create(@Valid @RequestBody CreateItem request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(items.create(request.id(), request.payload()));
    }

    @GetMapping("/items/{id}")
    public ResponseEntity<Item> find(@PathVariable UUID id) {
        return ResponseEntity.of(items.find(id));
    }
}
