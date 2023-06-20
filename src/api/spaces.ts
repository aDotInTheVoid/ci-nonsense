import { del, get, post, put } from "@/api/index";

export type SpaceID = string;

export interface APISpace {
  id: SpaceID;
  display_name: string;
}

export class Space {
  id: SpaceID;
  displayName: string;

  public constructor(id: SpaceID, displayName: string) {
    this.id = id;
    this.displayName = displayName;
  }

  public static parseFromAPI(apiSpace: APISpace): Space {
    return new Space(apiSpace.id, apiSpace.display_name);
  }
}

export async function spaces(): Promise<Map<SpaceID, Space>> {
  const apiSpaces = await get("space/get-all");
  const result = new Map<SpaceID, Space>();

  apiSpaces.forEach((apiSpace: APISpace) => {
    result.set(apiSpace.id, Space.parseFromAPI(apiSpace));
  });

  return result;
}

export async function createNewSpace(display_name: string): Promise<SpaceID> {
  return (await (await post("space/new", { display_name })).json()).id;
}

export async function getDisplayName(): Promise<string> {
  return (await get("space/name")).display_name;
}

export async function deleteSpace(id: SpaceID) {
  return await del("space/delete", { id });
}

export async function joinSpace(id: SpaceID) {
  return await put("space/join", { id });
}
