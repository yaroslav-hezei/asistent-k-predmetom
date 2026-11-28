"use client";

import { createContext, useContext, useEffect, type Dispatch, type SetStateAction } from "react";

export type ChatTitle = { pathname: string; name: string };
export const ChatTitleContext = createContext<Dispatch<SetStateAction<ChatTitle | null>> | null>(null);

export function CourseTitle({ pathname, name }: ChatTitle) {
  const setTitle = useContext(ChatTitleContext);
  useEffect(() => {
    setTitle?.({ pathname, name });
    return () => setTitle?.(current => current?.pathname === pathname && current.name === name ? null : current);
  }, [setTitle, pathname, name]);
  return null;
}
