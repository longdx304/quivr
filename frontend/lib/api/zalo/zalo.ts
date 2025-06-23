import { AxiosInstance } from "axios";

export const integrateBrainWithZalo = async (
  brainId: string,
  axiosInstance: AxiosInstance
): Promise<{ success: boolean; message: string; brain_id: string }> => {
  const response = await axiosInstance.post(`/zalo/integrate-brain/${brainId}`);

  return response.data;
};

export const getBrainZaloIntegration = async (
  brainId: string,
  axiosInstance: AxiosInstance
): Promise<{
  brain_id: string;
  integrated: boolean;
  integration_data: any;
}> => {
  const response = await axiosInstance.get(
    `/zalo/brain-integration/${brainId}`
  );

  return response.data;
};

export const removeBrainZaloIntegration = async (
  brainId: string,
  axiosInstance: AxiosInstance
): Promise<{ success: boolean; message: string; brain_id: string }> => {
  const response = await axiosInstance.delete(
    `/zalo/integrate-brain/${brainId}`
  );

  return response.data;
};
