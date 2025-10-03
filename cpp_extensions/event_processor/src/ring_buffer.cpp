#include "ring_buffer.hpp"
#include "event_processor.hpp"

namespace engagehub {
// Explicit instantiation for dynamic event buffer used by EventStreamProcessor
// (Size parameter 0 translates to runtime-sized buffer)
template class LockFreeRingBuffer<Event, 0>;
}
