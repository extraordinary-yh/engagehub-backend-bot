#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <type_traits>
#include <vector>

namespace engagehub {

constexpr std::size_t cache_line_size = 64;

namespace detail {

inline std::size_t round_up_to_power_of_two(std::size_t value) {
    if (value <= 1) {
        return 1;
    }
    --value;
    for (std::size_t i = 1; i < sizeof(std::size_t) * 8; i <<= 1) {
        value |= value >> i;
    }
    return value + 1;
}

} // namespace detail

template <typename T, std::size_t Size>
class LockFreeRingBuffer {
    static_assert(Size > 0, "Ring buffer size must be greater than zero");
    static_assert((Size & (Size - 1)) == 0, "Ring buffer size must be a power of two");

public:
    LockFreeRingBuffer();
    ~LockFreeRingBuffer();

    bool push(const T& value);
    bool push(T&& value);

    bool pop(T& result);

    std::size_t capacity() const noexcept { return Size; }
    bool empty() const noexcept;

private:
    template <typename U>
    bool emplace(U&& value);

    struct alignas(cache_line_size) Cell {
        std::atomic<std::size_t> sequence;
        typename std::aligned_storage<sizeof(T), alignof(T)>::type storage;
    };

    Cell buffer_[Size];
    alignas(cache_line_size) std::atomic<std::size_t> enqueue_pos_;
    alignas(cache_line_size) std::atomic<std::size_t> dequeue_pos_;
};

// Runtime-sized specialisation using Size == 0

template <typename T>
class LockFreeRingBuffer<T, 0> {
public:
    explicit LockFreeRingBuffer(std::size_t size)
        : size_(detail::round_up_to_power_of_two(size == 0 ? 1 : size)),
          mask_(size_ - 1),
          buffer_(size_),
          enqueue_pos_(0),
          dequeue_pos_(0) {
        for (std::size_t i = 0; i < size_; ++i) {
            buffer_[i].sequence.store(i, std::memory_order_relaxed);
        }
    }

    ~LockFreeRingBuffer() {
        T value;
        while (pop(value)) {
            // drain remaining items to invoke destructors
        }
    }

    bool push(const T& value) { return emplace(value); }
    bool push(T&& value) { return emplace(std::move(value)); }

    bool pop(T& result) {
        Cell* cell;
        std::size_t pos = dequeue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            cell = &buffer_[pos & mask_];
            const std::size_t seq = cell->sequence.load(std::memory_order_acquire);
            const intptr_t diff = static_cast<intptr_t>(seq) - static_cast<intptr_t>(pos + 1);
            if (diff == 0) {
                if (dequeue_pos_.compare_exchange_weak(pos, pos + 1, std::memory_order_relaxed)) {
                    break;
                }
            } else if (diff < 0) {
                return false;
            } else {
                pos = dequeue_pos_.load(std::memory_order_relaxed);
            }
        }
        result = std::move(*reinterpret_cast<T*>(&cell->storage));
        reinterpret_cast<T*>(&cell->storage)->~T();
        cell->sequence.store(pos + size_, std::memory_order_release);
        return true;
    }

    std::size_t capacity() const noexcept { return size_; }

    bool empty() const noexcept {
        return enqueue_pos_.load(std::memory_order_acquire) ==
               dequeue_pos_.load(std::memory_order_acquire);
    }

private:
    template <typename U>
    bool emplace(U&& value) {
        Cell* cell;
        std::size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            cell = &buffer_[pos & mask_];
            const std::size_t seq = cell->sequence.load(std::memory_order_acquire);
            const intptr_t diff = static_cast<intptr_t>(seq) - static_cast<intptr_t>(pos);
            if (diff == 0) {
                if (enqueue_pos_.compare_exchange_weak(pos, pos + 1, std::memory_order_relaxed)) {
                    break;
                }
            } else if (diff < 0) {
                return false;
            } else {
                pos = enqueue_pos_.load(std::memory_order_relaxed);
            }
        }
        new (&cell->storage) T(std::forward<U>(value));
        cell->sequence.store(pos + 1, std::memory_order_release);
        return true;
    }

    struct alignas(cache_line_size) Cell {
        std::atomic<std::size_t> sequence;
        typename std::aligned_storage<sizeof(T), alignof(T)>::type storage;
    };

    std::size_t size_;
    std::size_t mask_;
    std::vector<Cell> buffer_;
    alignas(cache_line_size) std::atomic<std::size_t> enqueue_pos_;
    alignas(cache_line_size) std::atomic<std::size_t> dequeue_pos_;
};

} // namespace engagehub

#include "ring_buffer.tpp"
