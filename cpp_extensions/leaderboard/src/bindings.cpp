#include "leaderboard.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace engagehub::leaderboard;

PYBIND11_MODULE(cpp_leaderboard, m) {
    py::class_<RankEntry>(m, "RankEntry")
        .def_property_readonly("user_id", [](const RankEntry& entry) { return entry.user_id; })
        .def_property_readonly("score", [](const RankEntry& entry) { return entry.score; })
        .def_property_readonly("rank", [](const RankEntry& entry) { return entry.rank; })
        .def_property_readonly("last_update", [](const RankEntry& entry) { return entry.last_update; });

    py::class_<Leaderboard>(m, "Leaderboard")
        .def(py::init<double, std::size_t>(),
             py::arg("decay_factor") = 0.95,
             py::arg("max_users") = 100000)
        .def("update_user", &Leaderboard::update_user,
             py::arg("user_id"),
             py::arg("points"),
             py::arg("timestamp"))
        .def("get_top_users", [](Leaderboard& self, std::size_t k) {
            const auto top = self.get_top_users(k);
            py::list result;
            for (const auto& entry : top) {
                py::dict obj;
                obj["user_id"] = entry.user_id;
                obj["score"] = entry.score;
                obj["rank"] = entry.rank;
                obj["last_update"] = entry.last_update;
                result.append(std::move(obj));
            }
            return result;
        }, py::arg("k"))
        .def("get_user_rank", [](Leaderboard& self, const std::string& user_id) -> py::object {
            if (auto info = self.get_user_rank(user_id)) {
                py::dict obj;
                obj["user_id"] = info->user_id;
                obj["score"] = info->score;
                obj["rank"] = info->rank;
                obj["last_update"] = info->last_update;
                return py::object(obj);
            }
            return py::object(py::none());
        }, py::arg("user_id"))
        .def("save_to_json", &Leaderboard::save_to_json, py::arg("filepath"))
        .def("load_from_json", &Leaderboard::load_from_json, py::arg("filepath"))
        .def("size", &Leaderboard::size)
        .def("get_current_time", &Leaderboard::get_current_time)
        .def("set_time_source", [](Leaderboard& self, py::object callable) {
            if (callable.is_none()) {
                self.set_time_source({});
                return;
            }
            py::function fn = py::reinterpret_borrow<py::function>(callable);
            self.set_time_source([fn]() -> std::int64_t {
                py::gil_scoped_acquire acquire;
                return fn().cast<std::int64_t>();
            });
        }, py::arg("callable"));
}
