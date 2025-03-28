cmake_minimum_required(VERSION 3.0)
project(PromoteSCN C)

set(CMAKE_C_STANDARD 11)

add_library(PromoteSCN SHARED library.c)
