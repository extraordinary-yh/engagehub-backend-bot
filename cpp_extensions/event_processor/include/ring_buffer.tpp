#pragma once

#include <thread>

namespace engagehub {

template <typename T, std::size_t Size>
LockFreeRingBuffer<T, Size>::LockFreeRingBuffer()
    : enqueue_pos_(0), dequeue_pos_(0) {
    for (std::size_t i = 0; i < Size; ++i) {
        buffer_[i].sequence.store(i, std::memory_order_relaxed);
    }
}

template <typename T, std::size_t Size>
LockFreeRingBuffer<T, Size>::~LockFreeRingBuffer() {
    T value;
    while (pop(value)) {
        // drain remaining items to destroy them
    }
}

template <typename T, std::size_t Size>
bool LockFreeRingBuffer<T, Size>::push(const T& value) {
    return emplace(value);
}

template <typename T, std::size_t Size>
bool LockFreeRingBuffer<T, Size>::push(T&& value) {
    return emplace(std::move(value));
}

template <typename T, std::size_t Size>
template <typename U>
bool LockFreeRingBuffer<T, Size>::emplace(U&& value) {
    Cell* cell;
    std::size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
    for (;;) {
        cell = &buffer_[pos & (Size - 1)];
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

template <typename T, std::size_t Size>
bool LockFreeRingBuffer<T, Size>::pop(T& result) {
    Cell* cell;
    std::size_t pos = dequeue_pos_.load(std::memory_order_relaxed);
    for (;;) {
        cell = &buffer_[pos & (Size - 1)];
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
    cell->sequence.store(pos + Size, std::memory_order_release);
    return true;
}

template <typename T, std::size_t Size>
bool LockFreeRingBuffer<T, Size>::empty() const noexcept {
    return enqueue_pos_.load(std::memory_order_acquire) ==
           dequeue_pos_.load(std::memory_order_acquire);
}

} // namespace engagehub
