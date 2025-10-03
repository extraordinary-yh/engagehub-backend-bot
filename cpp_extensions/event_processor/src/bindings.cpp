#include "event_processor.hpp"

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace engagehub;

PYBIND11_MODULE(cpp_event_processor, m) {
    py::class_<Event>(m, "Event")
        .def_property_readonly("event_type", [](const Event& e) { return e.event_type; })
        .def_property_readonly("user_id", [](const Event& e) { return e.user_id; })
        .def_property_readonly("channel_id", [](const Event& e) { return e.channel_id; })
        .def_property_readonly("timestamp", [](const Event& e) { return e.timestamp; });

    py::class_<EventStreamProcessor>(m, "EventStreamProcessor")
        .def(py::init<std::size_t, std::size_t, std::size_t, std::size_t>(),
             py::arg("buffer_size"),
             py::arg("num_threads"),
             py::arg("batch_size"),
             py::arg("flush_interval_ms"))
        .def("push_event", [](EventStreamProcessor& self,
                               const std::string& event_type,
                               const std::string& user_id,
                               const std::string& channel_id,
                               std::int64_t timestamp) {
            // Release GIL for better concurrency
            py::gil_scoped_release release;
            return self.push_event(event_type, user_id, channel_id, timestamp);
        }, py::arg("event_type"),
           py::arg("user_id"),
           py::arg("channel_id"),
           py::arg("timestamp"))
        .def("get_unique_users_last_hour", &EventStreamProcessor::get_unique_users_last_hour)
        .def("get_top_channels", [](EventStreamProcessor& self, std::size_t k) {
            const auto top = self.get_top_channels(k);
            py::list result;
            for (const auto& entry : top) {
                result.append(py::make_tuple(entry.first, entry.second));
            }
            return result;
        }, py::arg("k"))
        .def("set_flush_callback", [](EventStreamProcessor& self, py::object callback) {
            if (callback.is_none()) {
                self.set_flush_callback(nullptr);
                return;
            }
            py::function fn = callback;
            self.set_flush_callback([fn](std::vector<Event> events) {
                py::gil_scoped_acquire acquire;
                py::list payload;
                for (const auto& event : events) {
                    py::dict item;
                    item["type"] = event.event_type;
                    item["user_id"] = event.user_id;
                    item["channel_id"] = event.channel_id;
                    item["timestamp"] = event.timestamp;
                    payload.append(std::move(item));
                }
                fn(payload);
            });
        }, py::arg("callback"))
        .def("flush_now", [](EventStreamProcessor& self) {
            // Release GIL to avoid deadlock with callback threads
            py::gil_scoped_release release;
            self.flush_now();
        })
        .def("total_events_processed", &EventStreamProcessor::total_events_processed)
        .def("events_dropped", &EventStreamProcessor::events_dropped);
}
