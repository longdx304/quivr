import { useAxios } from "@/lib/hooks";

import {
  getBrainZaloIntegration,
  integrateBrainWithZalo,
  removeBrainZaloIntegration,
} from "./zalo";

// eslint-disable-next-line @typescript-eslint/explicit-module-boundary-types
export const useZaloApi = () => {
  const { axiosInstance } = useAxios();

  return {
    integrateBrainWithZalo: async (brainId: string) =>
      integrateBrainWithZalo(brainId, axiosInstance),
    getBrainZaloIntegration: async (brainId: string) =>
      getBrainZaloIntegration(brainId, axiosInstance),
    removeBrainZaloIntegration: async (brainId: string) =>
      removeBrainZaloIntegration(brainId, axiosInstance),
  };
};
