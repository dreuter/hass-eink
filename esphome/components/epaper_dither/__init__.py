import esphome.config_validation as cv
import esphome.codegen as cg

CODEOWNERS = []

epaper_dither_ns = cg.esphome_ns.namespace("epaper_dither")
DitherAlgorithm = epaper_dither_ns.enum("DitherAlgorithm")
EpaperDither = epaper_dither_ns.class_("EpaperDither", cg.Component)

DITHER_ALGORITHMS = {
    "floyd_steinberg": DitherAlgorithm.DITHER_FLOYD_STEINBERG,
    "atkinson":        DitherAlgorithm.DITHER_ATKINSON,
    "jarvis":          DitherAlgorithm.DITHER_JARVIS,
    "sierra":          DitherAlgorithm.DITHER_SIERRA,
}

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(EpaperDither),
    cv.Optional("algorithm",  default="atkinson"): cv.enum(DITHER_ALGORITHMS),
    cv.Optional("diffusion",  default=0.8): cv.float_range(min=0.0, max=1.0),
    cv.Optional("gamma",      default=2.2): cv.positive_float,
    cv.Optional("contrast",   default=1.0): cv.float_range(min=0.0, max=2.0),
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = cg.new_Pvariable(config[cv.CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_algorithm(config["algorithm"]))
    cg.add(var.set_diffusion(config["diffusion"]))
    cg.add(var.set_gamma(config["gamma"]))
    cg.add(var.set_contrast(config["contrast"]))
