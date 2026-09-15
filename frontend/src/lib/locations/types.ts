export type DistrictOption = {
  code: string;
  name: string;
  name_bn: string;
};

export type UpazilaOption = {
  code: string;
  district_code: string;
  name: string;
  name_bn: string;
};

export type BangladeshAreaOptions = {
  districts: DistrictOption[];
  upazilas: UpazilaOption[];
};
