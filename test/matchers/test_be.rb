require File.dirname(__FILE__) + "/../test_helper.rb"

describe "be(something)" do
  it "compares given with something, using ==" do
    1.should be(1)
    nil.should be(nil)
  end
end

describe "be_something" do
  
  %w( a ab aba a_a ab_ab ab_ab_ab babababab ).each do |p|
    describe "should be_#{p}" do
      it "passes if obj.#{p}? #=> true" do
        obj = Class.new do |klass|
          define_method("#{p}?") {true}
        end.new
        eval "obj.should be_#{p}"
      end
    end
    describe "should_not be_#{p}" do
      it "passes if obj.#{p}? #=> false" do
        obj = Class.new do |klass|
          define_method("#{p}?") {false}
        end.new
        eval "obj.should_not be_#{p}"
      end
    end
  end
  
end


describe "be_nil" do
  it "passes if given is nil" do
    nil.should be_nil
  end
  
  it "'should_not be_nil' passes if given is not nil" do
    1.should_not be_nil
  end
end

