package lab.{{PKG}}.contract;

import org.springframework.test.context.ActiveProfiles;

@ActiveProfiles("a")
class AContractTest extends ItemServiceContractTest {

    @Override
    protected String expectedImplementation() {
        return "a";
    }
}
