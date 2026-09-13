import { NextResponse, type NextRequest } from "next/server";

/**
 * Everything behind a session.
 *
 * The API is the real gate -- it verifies the signed token on every request,
 * and this cannot, since the signing secret belongs to the backend. What this
 * does is stop an unauthenticated visitor landing on a page that would render
 * a shell and then fail every call inside it; they get the login screen and a
 * way back to where they were going.
 *
 * It reads presence of the session cookie only. That works here because the
 * API and the app share a host (a cookie ignores the port); split them across
 * domains and this check stops seeing the cookie, at which point the redirect
 * has to come from the API's own 401 instead.
 */
const SESSION_COOKIE = "sahilli_session";

const PROTECTED = ["/msme", "/admin"];
const AUTH_PAGES = ["/login", "/signup"];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const signedIn = request.cookies.has(SESSION_COOKIE);

  if (!signedIn && PROTECTED.some((prefix) => pathname.startsWith(prefix))) {
    const login = new URL("/login", request.url);
    // Where they were heading, so signing in finishes the journey rather than
    // dumping them on a landing page to navigate again.
    login.searchParams.set("next", pathname + search);
    return NextResponse.redirect(login);
  }

  if (signedIn && AUTH_PAGES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.redirect(new URL("/msme", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/msme", "/msme/:path*", "/admin", "/admin/:path*", "/login", "/signup"],
};
