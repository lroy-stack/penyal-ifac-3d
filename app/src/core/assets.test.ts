import type { WebGLRenderer } from "three";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
import { describe, expect, it, vi } from "vitest";
import { BASIS_TRANSCODER_PATH, basisTranscoderPath, createGltfLoader, publicUrl } from "./assets";

const supportedExtensions = new Set(["WEBGL_compressed_texture_etc"]);

const fakeRenderer = {
  extensions: {
    has: (name: string) => supportedExtensions.has(name),
    get: () => null,
  },
} as unknown as WebGLRenderer;

describe("createGltfLoader", () => {
  it("wires a KTX2 loader with the local basis transcoder and detected support", () => {
    const { loader, dispose } = createGltfLoader(fakeRenderer);

    expect(loader.ktx2Loader).toBeInstanceOf(KTX2Loader);
    expect(loader.ktx2Loader?.transcoderPath).toBe(BASIS_TRANSCODER_PATH);
    expect(BASIS_TRANSCODER_PATH).toBe("/decoders/basis/");
    expect(loader.ktx2Loader?.workerConfig).toMatchObject({
      etc2Supported: true,
      dxtSupported: false,
    });
    dispose();
  });

  it("starts downloading the transcoder at once, and a failed download is not an unhandled rejection", async () => {
    const init = vi
      .spyOn(KTX2Loader.prototype, "init")
      .mockReturnValue(Promise.reject(new Error("offline")) as ReturnType<KTX2Loader["init"]>);
    const unhandled = vi.fn();
    process.on("unhandledRejection", unhandled);

    const { dispose } = createGltfLoader(fakeRenderer);
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(init).toHaveBeenCalledOnce();
    expect(unhandled).not.toHaveBeenCalled();
    process.off("unhandledRejection", unhandled);
    init.mockRestore();
    dispose();
  });

  it("wires the meshopt decoder", () => {
    const { loader, dispose } = createGltfLoader(fakeRenderer);

    expect(loader.meshoptDecoder).toBe(MeshoptDecoder);
    dispose();
  });

  it("disposes the shared KTX2 loader's worker pool", () => {
    const { loader, dispose } = createGltfLoader(fakeRenderer);
    const spy = vi.spyOn(loader.ktx2Loader as KTX2Loader, "dispose");

    dispose();

    expect(spy).toHaveBeenCalledOnce();
  });
});

describe("base-aware URLs", () => {
  it("prefixes the transcoder path with the deployment base", () => {
    expect(basisTranscoderPath("/penyal/")).toBe("/penyal/decoders/basis/");
    expect(basisTranscoderPath("/")).toBe("/decoders/basis/");
  });

  it("joins public paths without doubling slashes", () => {
    expect(publicUrl("assets/generated/trail.json", "/penyal/")).toBe(
      "/penyal/assets/generated/trail.json",
    );
    expect(publicUrl("/assets/x.json", "/")).toBe("/assets/x.json");
  });
});
